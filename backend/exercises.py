import secrets
import string
from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from pymongo.errors import DuplicateKeyError

from db import db
from ingest import hash_key
from models import Attempt, AttemptPublic, Exercise, SilenceRules
from workspace import get_route

router = APIRouter(prefix="/api")

ALPHABET = string.ascii_lowercase + string.digits
Required = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AssignIn(BaseModel):
    client_id: Required
    goal: Required
    cue_style: Literal["minimal", "standard"] = "standard"
    stay_silent_on_route: bool = True
    no_repeat: bool = True
    note: Optional[str] = None
    stop_rule: Required
    record_demo: bool = False


class NewAttemptIn(BaseModel):
    record_demo: bool = False


class AttemptCreated(BaseModel):
    # the only response that ever carries a plain key
    exercise: Exercise
    attempt: AttemptPublic
    key: str


class AttemptView(AttemptPublic):
    last_help_at: Optional[str] = None


class ExerciseView(Exercise):
    route_name: str
    attempts: List[AttemptView]


async def create_attempt(exercise_id: str, route_version: int, **extra) -> tuple[Attempt, str]:
    key = secrets.token_urlsafe(24)
    for _ in range(20):
        stream_id = "att-" + "".join(secrets.choice(ALPHABET) for _ in range(4))
        attempt = Attempt(exercise_id=exercise_id, status="not_started", stream_id=stream_id, key_hash=hash_key(key), route_version=route_version, **extra)
        try:
            await db.attempts.insert_one(attempt.to_mongo())
            return attempt, key
        except DuplicateKeyError:
            continue
    raise HTTPException(status_code=503, detail="Couldn't create a unique stream ID. Try again.")


async def get_exercise(exercise_id: str) -> Exercise:
    doc = await db.exercises.find_one({"id": exercise_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Exercise not found")
    exercise = Exercise.from_mongo(doc)
    await get_route(exercise.route_id)
    return exercise


def created(exercise: Exercise, attempt: Attempt, key: str) -> AttemptCreated:
    return AttemptCreated(exercise=exercise, attempt=AttemptPublic(**attempt.model_dump()), key=key)


@router.post("/routes/{route_id}/exercises", response_model=AttemptCreated, status_code=201)
async def assign_exercise(route_id: str, body: AssignIn):
    route = await get_route(route_id)
    if route.current_version < 1:
        raise HTTPException(status_code=422, detail="Save the route before assigning it")
    if not await db.clients.find_one({"id": body.client_id}):
        raise HTTPException(status_code=422, detail="Choose a client")
    note = (body.note or "").strip() or None
    exercise = Exercise(
        route_id=route.id,
        route_version=route.current_version,
        client_id=body.client_id,
        goal=body.goal,
        cue_style=body.cue_style,
        silence_rules=SilenceRules(stay_silent_on_route=body.stay_silent_on_route, no_repeat=body.no_repeat, note=note),
        stop_rule=body.stop_rule,
    )
    await db.exercises.insert_one(exercise.to_mongo())
    try:
        attempt, key = await create_attempt(exercise.id, route.current_version, record_demo=body.record_demo)
    except Exception:
        await db.exercises.delete_one({"id": exercise.id})
        raise HTTPException(status_code=500, detail="Couldn't assign the exercise. Nothing was saved. Try again.")
    return created(exercise, attempt, key)


@router.post("/exercises/{exercise_id}/attempts", response_model=AttemptCreated, status_code=201)
async def new_attempt(exercise_id: str, body: Optional[NewAttemptIn] = None):
    exercise = await get_exercise(exercise_id)
    route = await get_route(exercise.route_id)
    attempt, key = await create_attempt(exercise.id, route.current_version, record_demo=bool(body and body.record_demo))
    return created(exercise, attempt, key)


@router.get("/clients/{client_id}/exercises", response_model=List[ExerciseView])
async def client_exercises(client_id: str):
    if not await db.clients.find_one({"id": client_id}):
        raise HTTPException(status_code=404, detail="Client not found")
    routes = {r["id"]: r["name"] for r in await db.routes.find({"is_test": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    docs = await db.exercises.find({"client_id": client_id, "route_id": {"$in": list(routes)}}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    views = []
    for d in docs:
        ex = Exercise.from_mongo(d)
        attempts = await db.attempts.find({"exercise_id": ex.id}, {"_id": 0, "key_hash": 0}).sort("created_at", 1).to_list(1000)
        views.append(ExerciseView(**ex.model_dump(), route_name=routes[ex.route_id], attempts=[await attempt_view(a) for a in attempts]))
    return views


async def attempt_view(doc: dict) -> AttemptView:
    help_ev = await db.attempt_events.find_one({"attempt_id": doc["id"], "type": "help"}, {"_id": 0, "t": 1}, sort=[("seq", -1)])
    return AttemptView(**AttemptPublic.from_mongo(doc).model_dump(), last_help_at=help_ev["t"] if help_ev else None)