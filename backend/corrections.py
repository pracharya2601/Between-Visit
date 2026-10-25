"""Practitioner corrections on review items and route-memory versions (known entities). Versions are append-only."""
import uuid
from typing import Annotated, Callable, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from pymongo.errors import DuplicateKeyError

from cue_policy import SIDES, entity_position
from db import db
from models import Correction, RouteVersion, now_iso
from workspace import AUTHOR

router = APIRouter(prefix="/api")

Side = Literal["left", "right", "ahead"]


class CorrectionIn(BaseModel):
    action: Literal["confirm", "edit", "dismiss"]
    label: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]] = None
    side: Optional[Side] = None


def entity_facts(ev: dict, vision: Optional[dict], trail: list, reached: int, side: Optional[str] = None) -> dict:
    """Label, side, segment and start-relative position of the object a cue event is about."""
    d = ev.get("details") or {}
    vision = vision or {}
    label = (ev.get("entity") or "").strip().lower()
    seen = [e["relation"] for e in (vision.get("result") or {}).get("new_entities", []) if e["label"].strip().lower() == label]
    side = side or d.get("side") or (seen[0] if seen else "ahead")
    pos = (ev["pos_x"], ev["pos_z"]) if ev.get("pos_x") is not None and ev.get("pos_z") is not None else None
    origin = (trail[0]["x"], trail[0]["z"]) if trail else None
    depth = vision.get(SIDES[side][1])
    position = entity_position(pos, origin, vision.get("heading_deg"), side, depth if depth and depth > 0 else None)
    return {"label": label, "side": side, "segment": d.get("segment") or {"from": reached, "to": reached + 1}, "position": position}


async def checkpoints_reached_before(ev: dict) -> int:
    q = {"attempt_id": ev["attempt_id"], "type": "cue", "spoken": True, "checkpoint": {"$ne": None}, "seq": {"$lt": ev["seq"]}}
    return len(await db.attempt_events.distinct("checkpoint", q))


async def next_version(route_id: str, change: Callable[[list, int], list], note: str) -> RouteVersion:
    """Appends a new version copied from the route's latest one, with the known entities changed."""
    for _ in range(5):
        latest = await db.route_versions.find_one({"route_id": route_id}, {"_id": 0}, sort=[("version", -1)])
        if not latest:
            raise HTTPException(status_code=422, detail="Save the route before changing its memory")
        n = latest["version"] + 1
        v = RouteVersion(route_id=route_id, version=n, checkpoints=latest["checkpoints"], known_entities=change(list(latest.get("known_entities") or []), n),
                         author=AUTHOR, memory_id=latest.get("memory_id"), note=note)
        try:
            await db.route_versions.insert_one(v.to_mongo())
        except DuplicateKeyError:
            continue
        await db.routes.update_one({"id": route_id}, {"$max": {"current_version": n}})
        return v
    raise HTTPException(status_code=503, detail="Couldn't save the new version. Try again.")


def correction_out(c: dict) -> dict:
    return {k: c.get(k) for k in ("id", "attempt_event_id", "action", "author", "created_at", "new_route_version", "before", "after")}


@router.post("/attempt-events/{event_id}/correction", status_code=201)
async def correct(event_id: str, body: CorrectionIn):
    ev = await db.attempt_events.find_one({"id": event_id, "type": "cue"}, {"_id": 0})
    if not ev:
        raise HTTPException(status_code=404, detail="Item not found")
    if not ev.get("entity"):
        raise HTTPException(status_code=422, detail="This item isn't about an object")
    existing = await db.corrections.find_one({"attempt_event_id": event_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail={"message": "This item already has a correction", "correction": correction_out(existing)})
    attempt = await db.attempts.find_one({"id": ev["attempt_id"]}, {"_id": 0}) or {}
    ex = await db.exercises.find_one({"id": attempt.get("exercise_id")}, {"_id": 0, "route_id": 1}) or {}
    vision = await db.attempt_events.find_one({"id": ev.get("for_event_id")}, {"_id": 0}) if ev.get("for_event_id") else None
    reached = await checkpoints_reached_before(ev)
    facts = entity_facts(ev, vision, attempt.get("trail") or [], reached)
    before = {"label": facts["label"], "side": facts["side"]}
    after = None
    if body.action != "dismiss":
        side = body.side if body.action == "edit" and body.side else facts["side"]
        facts = entity_facts(ev, vision, attempt.get("trail") or [], reached, side)
        if body.action == "edit" and body.label:
            facts["label"] = body.label.lower()
        after = {"label": facts["label"], "side": facts["side"]}
    corr = Correction(attempt_event_id=event_id, attempt_id=ev["attempt_id"], action=body.action, author=AUTHOR, before=before, after=after)
    try:
        await db.corrections.insert_one(corr.to_mongo())
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail={"message": "This item already has a correction"})
    if after is None:
        return correction_out(corr.to_mongo())
    entity = {"id": str(uuid.uuid4()), **facts, "verified_by": AUTHOR, "verified_at": now_iso(), "from_event_id": event_id}
    try:
        v = await next_version(ex["route_id"], lambda ents, n: ents + [{**entity, "added_in": n}], f"{facts['label']} confirmed")
    except Exception:
        await db.corrections.delete_one({"id": corr.id})
        raise
    await db.corrections.update_one({"id": corr.id}, {"$set": {"new_route_version": v.version}})
    return {**correction_out(corr.to_mongo()), "new_route_version": v.version}


@router.post("/routes/{route_id}/known-entities/{entity_id}/remove", status_code=201)
async def remove_known(route_id: str, entity_id: str):
    latest = await db.route_versions.find_one({"route_id": route_id}, {"_id": 0}, sort=[("version", -1)])
    hit = next((e for e in (latest or {}).get("known_entities") or [] if isinstance(e, dict) and e.get("id") == entity_id), None)
    if not hit:
        raise HTTPException(status_code=404, detail="That object isn't in the route memory")
    v = await next_version(route_id, lambda ents, n: [e for e in ents if not (isinstance(e, dict) and e.get("id") == entity_id)], f"{hit['label']} removed")
    return {"version": v.version, "note": v.note}


def default_note(v: dict) -> str:
    return v.get("note") or ("route saved" if v["version"] == 1 else "checkpoints edited")


@router.get("/routes/{route_id}/history")
async def route_history(route_id: str):
    if not await db.routes.find_one({"id": route_id}):
        raise HTTPException(status_code=404, detail="Route not found")
    docs = await db.route_versions.find({"route_id": route_id}, {"_id": 0, "checkpoints": 0}).sort("version", -1).to_list(1000)
    known = [e for e in (docs[0].get("known_entities") if docs else []) or [] if isinstance(e, dict)]
    return {
        "versions": [{"version": d["version"], "note": default_note(d), "author": d["author"], "created_at": d["created_at"]} for d in docs],
        "known_entities": known,
        "current_version": docs[0]["version"] if docs else 0,
    }
