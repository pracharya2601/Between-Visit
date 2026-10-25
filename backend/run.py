from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, StringConstraints

import cue_runner
from db import db
from ingest import key_matches, push_guide, state_for
from models import Attempt, AttemptEvent, now_iso

router = APIRouter(prefix="/api")

TRANSITIONS = {
    "start": (("not_started",), "running"),
    "pause": (("running",), "paused"),
    "resume": (("paused",), "running"),
    "end": (("running", "paused"), "ended"),
}
CueText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=199)]


class RunState(BaseModel):
    status: str
    started_at: Optional[str]
    ended_at: Optional[str]
    elapsed_seconds: float
    glasses_live: bool
    seconds_since_glasses_frame: Optional[float]


class CueOut(BaseModel):
    seq: int
    t: str
    text: str
    priority: Optional[int]


class RunInfo(BaseModel):
    attempt_id: str
    stream_id: str
    goal: str
    checkpoints: List[str]
    stop_rule: str
    last_cue: Optional[CueOut]
    state: RunState


class CuesOut(BaseModel):
    cues: List[CueOut]
    state: RunState


class AckIn(BaseModel):
    spoken: bool
    reason: Optional[str] = None


class MessageIn(BaseModel):
    text: CueText


async def get_attempt(attempt_id: str) -> Attempt:
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    return Attempt.from_mongo(doc)


async def keyed_attempt(attempt_id: str, key: Optional[str]) -> Attempt:
    attempt = await get_attempt(attempt_id)
    if not key_matches(key, attempt.key_hash):
        raise HTTPException(status_code=401, detail="This link's key isn't valid.")
    return attempt


def elapsed(a: Attempt) -> float:
    return a.elapsed_seconds()


def run_state(a: Attempt) -> RunState:
    s = state_for(a.id)
    return RunState(
        status=a.status,
        started_at=a.started_at,
        ended_at=a.ended_at,
        elapsed_seconds=elapsed(a),
        glasses_live=s.ws is not None,
        seconds_since_glasses_frame=s.seconds_since_glasses_frame(),
    )


async def log_event(attempt_id: str, type_: str, **fields) -> AttemptEvent:
    ev = AttemptEvent(attempt_id=attempt_id, type=type_, **fields)
    await db.attempt_events.insert_one(ev.to_mongo())
    return ev


def cue_out(ev: dict) -> CueOut:
    return CueOut(seq=ev["seq"], t=ev["t"], text=ev["text"], priority=ev.get("priority"))


async def last_guide(attempt_id: str) -> Optional[dict]:
    return await db.attempt_events.find_one({"attempt_id": attempt_id, "type": "guide"}, {"_id": 0}, sort=[("seq", -1)])


Key = Annotated[Optional[str], Header(alias="X-Stream-Key")]


@router.get("/run/{attempt_id}", response_model=RunInfo)
async def run_info(attempt_id: str, x_stream_key: Key = None):
    a = await keyed_attempt(attempt_id, x_stream_key)
    ex = await db.exercises.find_one({"id": a.exercise_id}, {"_id": 0}) or {}
    version = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a.route_version}, {"_id": 0})
    names = [c["name"] for c in sorted((version or {}).get("checkpoints", []), key=lambda c: c["order"])]
    last = await last_guide(a.id)
    return RunInfo(
        attempt_id=a.id,
        stream_id=a.stream_id,
        goal=ex.get("goal", ""),
        checkpoints=names,
        stop_rule=ex.get("stop_rule", ""),
        last_cue=cue_out(last) if last else None,
        state=run_state(a),
    )


@router.get("/run/{attempt_id}/cues", response_model=CuesOut)
async def run_cues(attempt_id: str, after: int = 0, x_stream_key: Key = None):
    a = await keyed_attempt(attempt_id, x_stream_key)
    docs = await db.attempt_events.find({"attempt_id": a.id, "type": "guide", "seq": {"$gt": after}}, {"_id": 0}).sort("seq", 1).to_list(50)
    return CuesOut(cues=[cue_out(d) for d in docs], state=run_state(a))


@router.post("/run/{attempt_id}/cues/{seq}/ack", status_code=204)
async def ack_cue(attempt_id: str, seq: int, body: AckIn, x_stream_key: Key = None):
    a = await keyed_attempt(attempt_id, x_stream_key)
    changes = {"spoken": True, "suppressed_reason": None} if body.spoken else {"suppressed_reason": (body.reason or "not_spoken")[:40]}
    query = {"attempt_id": a.id, "type": "guide", "seq": seq}
    if not body.spoken:
        query["spoken"] = False
    await db.attempt_events.update_one(query, {"$set": changes})


@router.post("/run/{attempt_id}/help", status_code=201)
async def run_help(attempt_id: str, x_stream_key: Key = None):
    a = await keyed_attempt(attempt_id, x_stream_key)
    if a.status == "ended":
        raise HTTPException(status_code=409, detail="This run has ended")
    ev = await log_event(a.id, "help")
    return {"t": ev.t}


@router.post("/run/{attempt_id}/repeat")
async def run_repeat(attempt_id: str, x_stream_key: Key = None):
    a = await keyed_attempt(attempt_id, x_stream_key)
    if a.status == "ended":
        raise HTTPException(status_code=409, detail="This run has ended")
    last = await last_guide(a.id)
    if not last:
        return {"cue": None, "resent_to_glasses": False}
    sent = await push_guide(a.id, last["text"], last.get("priority") or 1)
    await log_event(a.id, "repeat", text=last["text"], priority=last.get("priority"), spoken=sent, suppressed_reason=None if sent else "glasses_not_live")
    return {"cue": cue_out(last), "resent_to_glasses": sent}


@router.post("/run/{attempt_id}/{action}", response_model=RunState)
async def run_transition(attempt_id: str, action: Literal["start", "pause", "resume", "end"], x_stream_key: Key = None):
    a = await keyed_attempt(attempt_id, x_stream_key)
    allowed, target = TRANSITIONS[action]
    if a.status not in allowed:
        raise HTTPException(status_code=409, detail=f"Can't {action} a run that is {a.status.replace('_', ' ')}")
    now = now_iso()
    changes = {"status": target}
    if action == "start":
        changes.update(started_at=now, running_since=now)
    elif action == "resume":
        changes["running_since"] = now
    if action in ("pause", "end") and a.status == "running":
        changes.update(active_seconds=elapsed(a), running_since=None)
    if action == "end":
        changes["ended_at"] = now
    res = await db.attempts.update_one({"id": a.id, "status": a.status}, {"$set": changes})
    if res.modified_count == 0:
        raise HTTPException(status_code=409, detail="The run changed. Try again.")
    await log_event(a.id, action)
    if target == "running":
        await cue_runner.on_running(a.id)
    else:
        cue_runner.on_stopped(a.id, ended=target == "ended")
    return run_state(await get_attempt(a.id))


@router.get("/attempts/{attempt_id}/events", response_model=List[AttemptEvent])
async def attempt_events(attempt_id: str, limit: int = 200):
    a = await get_attempt(attempt_id)
    docs = await db.attempt_events.find({"attempt_id": a.id}, {"_id": 0}).sort("seq", -1).to_list(min(max(limit, 1), 1000))
    return [AttemptEvent.from_mongo(d) for d in docs]


@router.post("/attempts/{attempt_id}/message", status_code=201)
async def message_client(attempt_id: str, body: MessageIn):
    a = await get_attempt(attempt_id)
    if a.status not in ("running", "paused"):
        raise HTTPException(status_code=409, detail="You can message a client only while the run is running or paused")
    sent = await push_guide(a.id, body.text, 1)
    ev = await log_event(a.id, "guide", text=body.text, priority=1, spoken=sent)
    return {"cue": cue_out(ev.model_dump()), "sent_to_glasses": sent}
