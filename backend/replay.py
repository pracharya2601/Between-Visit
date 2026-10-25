"""Demo replays: feed a recording's frames at their original timing through the normal vision → cue_policy → cue pipeline."""
import asyncio
import logging
import math
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
from review import ROUTINE, build_path, build_timeline, known_for_review, load_memory, memory_response
from corrections import is_scan
from cue_policy import alignment, to_route

LANDING_POINTS = 15_000
from sensors import SENSORS, sensors_for
from storage import get_object

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
DEMO_ROUTE = "Entrance → hallway turn → reception desk (synthetic)"
MAX_PUBLIC = 3
TTL = timedelta(hours=24)
BUSY = "Demo busy, try again in a minute."
NO_RECORDING = "No demo recording yet."
DEMO_SETTING = "website_demo_route"
NOT_READY = "This route needs a ready real recording, a saved 3D model and checkpoints to be the website demo."
CREATE_LOCK = asyncio.Lock()
TASKS: set = set()


class ReplayIn(BaseModel):
    on: Literal["v1", "latest"] = "latest"
    recording_id: Optional[str] = None


class DemoSettingIn(BaseModel):
    route_id: Optional[str] = None


def rec_out(r: dict) -> dict:
    return {"id": r["id"], "kind": r["kind"], "label": r["label"], "frame_count": len(r.get("frames") or []), "created_at": r["created_at"], "route_version": r.get("route_version")}


async def recordings_for(route_id: str) -> list:
    docs = await db.recordings.find({"route_id": route_id, "ready": True}, {"_id": 0}).to_list(100)
    real = sorted([r for r in docs if r["kind"] == "real"], key=lambda r: r["created_at"], reverse=True)
    return real + [r for r in docs if r["kind"] == "synthetic"]


async def synthetic_route() -> dict:
    route = await db.routes.find_one({"name": DEMO_ROUTE, "is_test": {"$ne": True}}, {"_id": 0})
    if not route:
        raise HTTPException(status_code=404, detail=NO_RECORDING)
    return route


def demo_poses(frames: list, scan: bool) -> list:
    """Recording poses moved into the route frame by the shared alignment; [] when it can't be aligned."""
    raw = [f for f in frames if (f.get("pose") or {}).get("x") is not None and f["pose"].get("z") is not None]
    al = alignment([(f["pose"]["x"], f["pose"]["z"]) for f in raw], scan)
    if al is None:
        return []
    turn = math.degrees(math.atan2(al[3], al[2]))
    return [[*(round(v, 3) for v in to_route(al, f["pose"]["x"], f["pose"]["z"])), round(((f["pose"].get("heading_deg") or 0) + turn) % 360, 1), f["t_offset_ms"]] for f in raw]


async def real_demo(route_id: Optional[str]) -> Optional[tuple]:
    """(route, latest version, latest real recording, poses) when the chosen route has everything the website demo needs; None → synthetic demo."""
    route = await db.routes.find_one({"id": route_id, "is_test": {"$ne": True}}, {"_id": 0}) if route_id else None
    if not route or route["name"] == DEMO_ROUTE:
        return None
    v = await db.route_versions.find_one({"route_id": route["id"], "version": route.get("current_version")}, {"_id": 0}) or {}
    if not v.get("checkpoints") or not v.get("memory_id") or not await db.route_memories.find_one({"id": v["memory_id"]}, {"_id": 0, "id": 1}):
        return None
    rec = await db.recordings.find_one({"route_id": route["id"], "kind": "real", "ready": True}, {"_id": 0}, sort=[("created_at", -1)])
    poses = demo_poses(rec.get("frames") or [], await is_scan(v)) if rec else []
    return (route, v, rec, poses) if len(poses) >= 2 else None


async def chosen_demo() -> Optional[tuple]:
    s = await db.settings.find_one({"key": DEMO_SETTING}, {"_id": 0}) or {}
    return await real_demo(s.get("route_id"))


async def demo_route() -> dict:
    real = await chosen_demo()
    return real[0] if real else await synthetic_route()


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


async def three_for(a: dict, v: dict, route_id, heading):
    """The 3D 'three' shape (saved model + shared alignment) for a run or replay; (None, items, scan) without a 3D model."""
    events = await db.attempt_events.find({"attempt_id": a["id"]}, {"_id": 0}).sort("seq", 1).to_list(5000)
    scan = await is_scan(v) if v else False
    started = a.get("started_at")
    items, _ = build_timeline(events, datetime.fromisoformat(started).timestamp() if started else 0.0, a.get("trail") or [], {}, scan)
    if not v.get("memory_id"):
        return None, items, scan
    path = await build_path(a, v, items, await known_for_review(v, {}, route_id))
    if path["mode"] != "3d":
        return None, items, scan
    return {"scene": path["scene"], "run_trail": path["run_trail"], "floor_y": path["floor_y"], "heading_deg": heading,
            "dots": [{"id": i["id"], "category": i["category"], "pos": i["pos"], "text": i["text"], "reason": i["reason"]} for i in items if i["category"] in ("spoken", "suppressed") and i["pos"]],
            "entities": [{"id": e["id"], "label": e["label"], "pos": e["pos"]} for e in path["entities"] if e.get("pos")]}, items, scan


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
    fr = rec["frames"][frame] if 0 <= frame < len(rec["frames"]) else {}
    three, _, _ = await three_for(a, v, ex.get("route_id"), (fr.get("pose") or {}).get("heading_deg"))
    return {
        "attempt_id": attempt_id, "status": a["status"], "public": a.get("public", False), "route_name": route.get("name"), "three": three,
        "version": a["route_version"], "version_line": version_line(a["route_version"], route.get("current_version") or a["route_version"]),
        "recording": {"kind": rec["kind"], "label": rec["label"], "frame_count": len(rec["frames"]), "model_label": (three or {}).get("scene", {}).get("model_label")},
        "frame_index": frame, "frame_url": f"/api/replays/{attempt_id}/frames/{frame}" if frame >= 0 else None,
        "caption": {"seq": spoken[-1]["seq"], "text": spoken[-1]["text"]} if spoken else None,
        "cues_spoken": len(spoken), "cues_held_back": sum(not c.get("spoken") and c.get("suppressed_reason") not in ROUTINE for c in cues),
        "last_checkpoint": next((c["checkpoint"] for c in reversed(spoken) if c.get("checkpoint")), None),
        "reached_checkpoints": list(dict.fromkeys(c["checkpoint"] for c in spoken if c.get("checkpoint"))),
        "path": [[round(p["x"] - ox, 2), round(p["z"] - oz, 2)] for p in trail],
        "checkpoints": [{"order": c["order"], "name": c["name"], "position": pos.get(c["id"])} for c in sorted(v.get("checkpoints", []), key=lambda c: c["order"])],
        "entities": [{"label": e["entity"]["label"], "side": e["entity"]["side"], "position": e["entity"]["position"]} for e in ents],
        "review_path": f"/review/{attempt_id}" if a["status"] == "ended" else None,
    }


async def real_scene(route: dict, v: dict, poses: list) -> Optional[dict]:
    loaded = await load_memory(v["memory_id"])
    if not loaded:
        return None
    mem, meta = loaded
    pos = await checkpoint_positions(v)
    chair = next((e for e in v.get("known_entities") or [] if isinstance(e, dict) and e.get("label") == "chair" and e.get("position")), None)
    ex_ids = [e["id"] for e in await db.exercises.find({"route_id": route["id"]}, {"_id": 0, "id": 1}).to_list(100)]
    att = await db.attempts.find_one({"exercise_id": {"$in": ex_ids}, "replay": {"$ne": True}, "status": "ended"}, {"_id": 0, "id": 1}, sort=[("created_at", -1)])
    return {
        "scene": {"points": mem["point_count"], "points_sent": min(mem["point_count"], LANDING_POINTS), "planes": meta.get("planes", []),
                  "trail": [p[:3] for p in meta.get("trail") or []] or [[p[0], 0.0, p[1]] for p in poses],
                  "metres_walked": mem.get("trail_m") or 0.0, "rgb": bool(mem.get("colors_path")),
                  "checkpoints": [{"id": c["id"], "order": c["order"], "name": c["name"], "position": [pos[c["id"]]["x"], 0.0, pos[c["id"]]["z"]] if pos.get(c["id"]) else None} for c in v.get("checkpoints", [])]},
        "poses": poses,
        "chair": {"label": "chair", "pos": chair["position"]} if chair else None,
        "review_attempt_id": att and att["id"],
    }


@router.get("/demo/setting")
async def demo_setting():
    s = await db.settings.find_one({"key": DEMO_SETTING}, {"_id": 0}) or {}
    real = await real_demo(s.get("route_id"))
    syn = await db.routes.find_one({"name": DEMO_ROUTE, "is_test": {"$ne": True}}, {"_id": 0, "id": 1}) or {}
    return {"route_id": s.get("route_id"), "synthetic_route_id": syn.get("id"), "active_route_id": real[0]["id"] if real else syn.get("id"), "using_synthetic": real is None}


@router.put("/demo/setting")
async def set_demo_setting(body: DemoSettingIn):
    if body.route_id:
        route = await db.routes.find_one({"id": body.route_id, "is_test": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        if route["name"] != DEMO_ROUTE and not await real_demo(route["id"]):
            raise HTTPException(status_code=409, detail=NOT_READY)
        await db.settings.update_one({"key": DEMO_SETTING}, {"$set": {"key": DEMO_SETTING, "route_id": route["id"], "updated_at": now_iso()}}, upsert=True)
    else:
        await db.settings.delete_one({"key": DEMO_SETTING})
    return await demo_setting()


@router.get("/demo/scene")
async def demo_scene():
    """Public, read-only data for the landing loop: stored model, synthetic trail, v2 chair, review rows source. No attempts, no AI."""
    real = await chosen_demo()
    out = await real_scene(real[0], real[1], real[3]) if real else None
    if out:
        return out
    route = await synthetic_route()
    v2 = await db.route_versions.find_one({"route_id": route["id"], "version": route["current_version"]}, {"_id": 0}) or {}
    loaded = await load_memory(v2["memory_id"]) if v2.get("memory_id") else None
    rec = await db.recordings.find_one({"route_id": route["id"], "kind": "synthetic", "ready": True}, {"_id": 0, "frames": 1})
    if not loaded or not rec:
        raise HTTPException(status_code=404, detail=NO_RECORDING)
    mem, meta = loaded
    pos = await checkpoint_positions(v2)
    chair = next((e for e in v2.get("known_entities") or [] if isinstance(e, dict) and e.get("label") == "chair" and e.get("position")), None)
    ex = await db.exercises.find_one({"route_id": route["id"]}, {"_id": 0, "id": 1})
    att = await db.attempts.find_one({"exercise_id": ex and ex["id"], "replay": {"$ne": True}, "status": "ended"}, {"_id": 0, "id": 1}, sort=[("created_at", 1)])
    return {
        "scene": {"points": mem["point_count"], "points_sent": min(mem["point_count"], LANDING_POINTS), "planes": meta.get("planes", []), "trail": [p[:3] for p in meta.get("trail") or []],
                  "metres_walked": mem["trail_m"], "rgb": bool(mem.get("colors_path")),
                  "checkpoints": [{"id": c["id"], "order": c["order"], "name": c["name"], "position": [pos[c["id"]]["x"], 0.0, pos[c["id"]]["z"]] if pos.get(c["id"]) else None} for c in v2.get("checkpoints", [])]},
        "poses": [[f["pose"]["x"], f["pose"]["z"], f["pose"].get("heading_deg") or 0, f["t_offset_ms"]] for f in rec["frames"] if f["pose"].get("x") is not None],
        "chair": {"label": "chair", "pos": chair["position"]} if chair else None,
        "review_attempt_id": att and att["id"],
    }


@router.get("/demo/points")
async def demo_points(colors: bool = False):
    real = await chosen_demo()
    route = real[0] if real and await load_memory(real[1]["memory_id"]) else await synthetic_route()
    v2 = await db.route_versions.find_one({"route_id": route["id"], "version": route["current_version"]}, {"_id": 0, "memory_id": 1}) or {}
    return await memory_response(v2, colors, cap=LANDING_POINTS)


@router.get("/replays/{attempt_id}/points")
async def replay_points(attempt_id: str, colors: bool = False):
    a = await replay_attempt(attempt_id)
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0, "route_id": 1}) or {}
    v = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a["route_version"]}, {"_id": 0, "memory_id": 1}) or {}
    return await memory_response(v, colors)


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
