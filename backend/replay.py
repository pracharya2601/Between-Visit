"""Demo replays: feed a recording's frames at their original timing through the normal vision → cue_policy → cue pipeline."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

import cue_runner
import vision_worker
from db import db
from exercises import create_attempt
from ingest import state_for
from machine import checkpoint_positions, machine_entity
from models import AttemptEvent, now_iso
from review import ROUTINE
from sensors import SENSORS, sensors_for
from storage import get_object

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
DEMO_ROUTE = "Entrance → hallway turn → reception desk (synthetic)"
MAX_PUBLIC = 3
TTL = timedelta(hours=24)
BUSY = "Demo busy, try again in a minute."
NO_RECORDING = "No demo recording yet."
CREATE_LOCK = asyncio.Lock()
TASKS: set = set()


class ReplayIn(BaseModel):
    on: Literal["v1", "latest"] = "latest"
    recording_id: Optional[str] = None


def rec_out(r: dict) -> dict:
    return {"id": r["id"], "kind": r["kind"], "label": r["label"], "frame_count": len(r.get("frames") or []), "created_at": r["created_at"], "route_version": r.get("route_version")}


async def recordings_for(route_id: str) -> list:
    docs = await db.recordings.find({"route_id": route_id, "ready": True}, {"_id": 0}).to_list(100)
    real = sorted([r for r in docs if r["kind"] == "real"], key=lambda r: r["created_at"], reverse=True)
    return real + [r for r in docs if r["kind"] == "synthetic"]


async def demo_route() -> dict:
    route = await db.routes.find_one({"name": DEMO_ROUTE, "is_test": {"$ne": True}}, {"_id": 0})
    if not route:
        raise HTTPException(status_code=404, detail=NO_RECORDING)
    return route


def version_line(n: int, latest: int) -> str:
    return "Replaying on v1 (before corrections)" if n == 1 and latest > 1 else f"Replaying on v{n} (latest)" if n == latest else f"Replaying on v{n}"


def _set_sensors(attempt_id: str, f: dict):
    s, now, p, d = sensors_for(attempt_id), __import__("time").time(), f.get("pose") or {}, f.get("depth") or {}
    if p.get("x") is not None and p.get("z") is not None:
        pose = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, float(p["x"]), 0.0, float(p["z"]), 1.0]
        s.phone = {"ar_pose": pose, "heading_deg": p.get("heading_deg"), "ar_tracking": p.get("ar_tracking")}
        s.phone_at = now
    if any(d.get(k) is not None for k in ("left", "centre", "right")):
        s.depth, s.depth_at = {k: d.get(k) for k in ("left", "centre", "right")}, now


async def _end(attempt_id: str):
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not doc or doc["status"] == "ended":
        return
    from models import Attempt
    a = Attempt.from_mongo(doc)
    await db.attempts.update_one({"id": a.id}, {"$set": {"status": "ended", "ended_at": now_iso(), "active_seconds": a.elapsed_seconds(), "running_since": None}})
    await db.attempt_events.insert_one(AttemptEvent(attempt_id=a.id, type="end").to_mongo())
    cue_runner.on_stopped(a.id, ended=True)
    SENSORS.pop(a.id, None)


async def _feed(attempt_id: str, frames: list):
    """Replays never record: the attempt has replay=True, so vision_worker skips the recording hook."""
    jpegs = [await get_object(f["path"]) for f in frames]
    queue: asyncio.Queue = asyncio.Queue()

    async def consume():
        while (item := await queue.get()) is not None:
            i, jpeg, f = item
            _set_sensors(attempt_id, f)
            try:
                await vision_worker.analyse(attempt_id, jpeg, f.get("source") or "glasses")
            except Exception:
                logger.exception("Replay analysis failed")
            await db.attempts.update_one({"id": attempt_id}, {"$set": {"replay_analysed": i + 1}})

    worker = asyncio.create_task(consume())
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    for i, (f, jpeg) in enumerate(zip(frames, jpegs)):
        delay = t0 + f["t_offset_ms"] / 1000 - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)
        fed = int((loop.time() - t0) * 1000)
        state_for(attempt_id).accept_frame(len(jpeg), src="phone" if f.get("source") == "phone" else "glasses")
        p = f.get("pose") or {}
        update = {"$set": {"replay_frame": i}, "$push": {"replay_fed_ms": fed}}
        if p.get("x") is not None and p.get("z") is not None:
            update["$push"]["trail"] = {"x": p["x"], "z": p["z"], "t": now_iso()}
        res = await db.attempts.update_one({"id": attempt_id, "status": "running"}, update)
        if res.matched_count == 0:
            break
        queue.put_nowait((i, jpeg, f))
    queue.put_nowait(None)
    await worker
    await _end(attempt_id)


def _spawn(coro):
    t = asyncio.create_task(coro)
    TASKS.add(t)
    t.add_done_callback(lambda task: (TASKS.discard(task), task.exception() and logger.warning("Replay failed: %s", type(task.exception()).__name__)))


async def start_replay(route: dict, body: ReplayIn, public: bool) -> dict:
    recs = await recordings_for(route["id"])
    if not recs:
        raise HTTPException(status_code=404, detail=NO_RECORDING)
    rec = next((r for r in recs if r["id"] == body.recording_id), None) if body.recording_id else recs[0]
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    version = 1 if body.on == "v1" else route["current_version"]
    async with CREATE_LOCK:
        if public and await db.attempts.count_documents({"replay": True, "public": True, "status": "running"}) >= MAX_PUBLIC:
            raise HTTPException(status_code=429, detail=BUSY)
        attempt, _ = await create_attempt(rec["exercise_id"], version, replay=True, recording_id=rec["id"], public=public)
        now = now_iso()
        await db.attempts.update_one({"id": attempt.id}, {"$set": {"status": "running", "started_at": now, "running_since": now, "replay_fed_ms": [], "replay_frame": -1}})
    await db.attempt_events.insert_one(AttemptEvent(attempt_id=attempt.id, type="start").to_mongo())
    await cue_runner.on_running(attempt.id)
    _spawn(_feed(attempt.id, rec["frames"]))
    return {"attempt_id": attempt.id}


@router.get("/routes/{route_id}/recordings")
async def route_recordings(route_id: str):
    return [rec_out(r) for r in await recordings_for(route_id)]


@router.post("/routes/{route_id}/replays", status_code=201)
async def practitioner_replay(route_id: str, body: ReplayIn):
    route = await db.routes.find_one({"id": route_id, "is_test": {"$ne": True}}, {"_id": 0})
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return await start_replay(route, body, public=False)


@router.get("/demo")
async def demo_info():
    route = await demo_route()
    recs = await recordings_for(route["id"])
    if not recs:
        raise HTTPException(status_code=404, detail=NO_RECORDING)
    return {"route_id": route["id"], "route_name": route["name"], "current_version": route["current_version"], "recordings": [rec_out(r) for r in recs]}


@router.post("/demo/replays", status_code=201)
async def public_replay(body: ReplayIn):
    return await start_replay(await demo_route(), body, public=True)


async def replay_attempt(attempt_id: str) -> dict:
    doc = await db.attempts.find_one({"id": attempt_id, "replay": True}, {"_id": 0, "key_hash": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Replay not found")
    return doc


@router.get("/replays/{attempt_id}")
async def replay_state(attempt_id: str):
    a = await replay_attempt(attempt_id)
    rec = await db.recordings.find_one({"id": a["recording_id"]}, {"_id": 0}) or {"frames": [], "label": "", "kind": "real"}
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0, "route_id": 1}) or {}
    route = await db.routes.find_one({"id": ex.get("route_id")}, {"_id": 0, "name": 1, "current_version": 1}) or {}
    v = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a["route_version"]}, {"_id": 0}) or {}
    cues = await db.attempt_events.find({"attempt_id": attempt_id, "type": "cue"}, {"_id": 0, "seq": 1, "text": 1, "spoken": 1, "suppressed_reason": 1, "checkpoint": 1}).sort("seq", 1).to_list(2000)
    spoken = [c for c in cues if c.get("spoken")]
    trail = a.get("trail") or []
    ox, oz = (trail[0]["x"], trail[0]["z"]) if trail else (0.0, 0.0)
    pos = await checkpoint_positions(v) if v else {}
    ents = [machine_entity(ex.get("route_id"), v["version"], e) for e in v.get("known_entities") or [] if isinstance(e, dict)] if v else []
    frame = a.get("replay_frame", -1)
    return {
        "attempt_id": attempt_id, "status": a["status"], "public": a.get("public", False), "route_name": route.get("name"),
        "version": a["route_version"], "version_line": version_line(a["route_version"], route.get("current_version") or a["route_version"]),
        "recording": {"kind": rec["kind"], "label": rec["label"], "frame_count": len(rec["frames"])},
        "frame_index": frame, "frame_url": f"/api/replays/{attempt_id}/frames/{frame}" if frame >= 0 else None,
        "caption": {"seq": spoken[-1]["seq"], "text": spoken[-1]["text"]} if spoken else None,
        "cues_spoken": len(spoken), "cues_held_back": sum(not c.get("spoken") and c.get("suppressed_reason") not in ROUTINE for c in cues),
        "last_checkpoint": next((c["checkpoint"] for c in reversed(spoken) if c.get("checkpoint")), None),
        "path": [[round(p["x"] - ox, 2), round(p["z"] - oz, 2)] for p in trail],
        "checkpoints": [{"order": c["order"], "name": c["name"], "position": pos.get(c["id"])} for c in sorted(v.get("checkpoints", []), key=lambda c: c["order"])],
        "entities": [{"label": e["entity"]["label"], "side": e["entity"]["side"], "position": e["entity"]["position"]} for e in ents],
        "review_path": f"/review/{attempt_id}" if a["status"] == "ended" else None,
    }


@router.get("/replays/{attempt_id}/frames/{index}")
async def replay_frame(attempt_id: str, index: int):
    a = await replay_attempt(attempt_id)
    rec = await db.recordings.find_one({"id": a["recording_id"]}, {"_id": 0, "frames": 1}) or {"frames": []}
    if index < 0 or index > a.get("replay_frame", -1) or index >= len(rec["frames"]):
        raise HTTPException(status_code=404, detail="Frame not found")
    return Response(await get_object(rec["frames"][index]["path"]), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


async def sweep_public_replays(now: Optional[datetime] = None) -> int:
    """Deletes public replays older than 24 h with their events; never practitioner replays or ones with corrections or a saved note."""
    cutoff = ((now or datetime.now(timezone.utc)) - TTL).isoformat()
    deleted = 0
    for a in await db.attempts.find({"replay": True, "public": True, "created_at": {"$lt": cutoff}}, {"_id": 0, "id": 1}).to_list(10000):
        ids = [e["id"] for e in await db.attempt_events.find({"attempt_id": a["id"]}, {"_id": 0, "id": 1}).to_list(100000)]
        if await db.progress_notes.find_one({"attempt_id": a["id"]}) or await db.corrections.find_one({"attempt_event_id": {"$in": ids}}):
            continue
        await db.attempt_events.delete_many({"attempt_id": a["id"]})
        await db.attempts.delete_one({"id": a["id"]})
        cue_runner.on_stopped(a["id"], ended=True)
        deleted += 1
    return deleted


async def sweep_loop():
    while True:
        try:
            n = await sweep_public_replays()
            if n:
                logger.info("Swept %d public replays", n)
        except Exception:
            logger.exception("Replay sweep failed")
        await asyncio.sleep(600)


async def end_orphan_replays():
    """Replays whose feeder died with a restart are ended so they don't hold a public slot."""
    for a in await db.attempts.find({"replay": True, "status": {"$ne": "ended"}}, {"_id": 0, "id": 1}).to_list(1000):
        await _end(a["id"])
