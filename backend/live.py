"""Watch live (practitioner): the run's 3D view, caption and newest glasses picture. In-memory only; frames are never stored."""
import math
import time

import numpy as np
from fastapi import APIRouter, HTTPException, Response

from cue_policy import alignment
from db import db
from ingest import state_for
from replay import ROUTINE, three_for
from review import memory_response
from sensors import sensors_for
from teach import BROWSER_POINTS, TeachMap, add_points

router = APIRouter(prefix="/api")

LIVE_POINTS = 100_000
LIVE_S = 3.0
FRAMES: dict = {}
MAPS: dict = {}
WANTS_POINTS: dict = {}


def on_frame(attempt_id: str, data: bytes):
    """Keeps only the newest frame of a run, in memory."""
    FRAMES[attempt_id] = (time.time(), data)


def on_depth(attempt_id: str, paired):
    """Routes without 3D memory: grow a live point map from DPT1 (same add_points as teach), capped at 100k."""
    if not WANTS_POINTS.get(attempt_id) or not paired or paired[3] != "normal" or not paired[2]:
        return
    m = MAPS.setdefault(attempt_id, TeachMap())
    if len(m.points) < LIVE_POINTS:
        add_points(m, paired[0], paired[1], paired[2])
        del m.points[LIVE_POINTS:]


async def on_running(attempt_id: str):
    a = await db.attempts.find_one({"id": attempt_id}, {"_id": 0, "exercise_id": 1, "route_version": 1})
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0, "route_id": 1}) or {}
    v = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a["route_version"]}, {"_id": 0, "memory_id": 1}) or {}
    WANTS_POINTS[attempt_id] = not v.get("memory_id")


def drop(attempt_id: str):
    """Run ended: the live picture and the live point map are dropped."""
    FRAMES.pop(attempt_id, None)
    MAPS.pop(attempt_id, None)
    WANTS_POINTS.pop(attempt_id, None)


async def live_attempt(attempt_id: str) -> dict:
    a = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not a or a.get("replay"):
        raise HTTPException(status_code=404, detail="Run not found")
    return a


def _live_three(a: dict, items: list, heading):
    """No saved model: the live points (world frame) or, without depth, the trail on a floor grid."""
    trail = [(p["x"], p["z"]) for p in a.get("trail") or []]
    pose = sensors_for(a["id"]).phone.get("ar_pose")
    m = MAPS.get(a["id"])
    n = len(m.points) if m else 0
    floor = (pose[13] - 1.4) if pose else 0.0
    if m and n:
        floor = float(np.percentile(np.asarray(m.points)[:, 1], 2))
    run = [[x, floor + 0.05, z] for x, z in trail]
    metres = sum(math.dist(p, q) for p, q in zip(trail, trail[1:]))
    return {"scene": {"points": n, "points_sent": min(n, BROWSER_POINTS), "planes": [], "trail": run, "metres_walked": round(metres, 2), "checkpoints": [],
                      "rgb": False, "grid": n == 0, "live_points": True},
            "run_trail": run, "floor_y": floor, "heading_deg": heading,
            "dots": [{"id": i["id"], "category": i["category"], "pos": i["pos"], "text": i["text"], "reason": i["reason"]} for i in items if i["category"] in ("spoken", "suppressed") and i["pos"]],
            "entities": []}


@router.get("/attempts/{attempt_id}/live")
async def attempt_live(attempt_id: str):
    a = await live_attempt(attempt_id)
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0, "route_id": 1, "client_id": 1}) or {}
    route = await db.routes.find_one({"id": ex.get("route_id")}, {"_id": 0, "name": 1}) or {}
    v = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a["route_version"]}, {"_id": 0}) or {}
    snap = sensors_for(attempt_id).snapshot()
    heading = snap.get("heading_deg")
    three, items, scan = await three_for(a, v, ex.get("route_id"), heading)
    if three and heading is not None:
        al = alignment([(p["x"], p["z"]) for p in a.get("trail") or []], scan)
        three["heading_deg"] = heading + (math.degrees(math.atan2(al[3], al[2])) if al else 0.0)
    if not three:
        three = _live_three(a, items, heading)
    cues = [i for i in items if i["category"] in ("spoken", "suppressed")]
    events = await db.attempt_events.find({"attempt_id": attempt_id, "type": "cue"}, {"_id": 0, "seq": 1, "text": 1, "spoken": 1, "suppressed_reason": 1, "checkpoint": 1}).sort("seq", 1).to_list(5000)
    spoken = [c for c in events if c.get("spoken")]
    last = state_for(attempt_id).last_frame_at
    active = a["status"] in ("running", "paused")
    return {
        "attempt_id": attempt_id, "status": a["status"], "route_name": route.get("name"), "client_id": ex.get("client_id"), "version": a["route_version"],
        "live": bool(active and last and time.time() - last <= LIVE_S), "three": three, "saved_model": bool(v.get("memory_id")),
        "caption": {"seq": spoken[-1]["seq"], "text": spoken[-1]["text"]} if spoken else None,
        "cues_spoken": len(spoken), "cues_held_back": sum(not c.get("spoken") and c.get("suppressed_reason") not in ROUTINE for c in events),
        "last_checkpoint": next((c["checkpoint"] for c in reversed(spoken) if c.get("checkpoint")), None),
        "reached_checkpoints": list(dict.fromkeys(c["checkpoint"] for c in spoken if c.get("checkpoint"))),
        "dots": len(cues), "frame_url": f"/api/attempts/{attempt_id}/live-frame" if active and attempt_id in FRAMES else None,
        "review_path": f"/review/{attempt_id}" if a["status"] == "ended" else None,
    }


@router.get("/attempts/{attempt_id}/live/points")
async def attempt_live_points(attempt_id: str, colors: bool = False):
    a = await live_attempt(attempt_id)
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0, "route_id": 1}) or {}
    v = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a["route_version"]}, {"_id": 0, "memory_id": 1}) or {}
    if v.get("memory_id"):
        return await memory_response(v, colors)
    m = MAPS.get(attempt_id)
    pts = np.asarray(m.points if m else [], dtype="<f4").reshape(-1, 3)
    if len(pts) > BROWSER_POINTS:
        pts = pts[np.linspace(0, len(pts) - 1, BROWSER_POINTS).astype(np.int64)]
    return Response(content=pts.tobytes(), media_type="application/octet-stream", headers={"X-Point-Count": str(len(pts)), "Cache-Control": "no-store"})


@router.get("/attempts/{attempt_id}/live-frame")
async def attempt_live_frame(attempt_id: str):
    a = await live_attempt(attempt_id)
    f = FRAMES.get(attempt_id)
    if a["status"] not in ("running", "paused") or not f:
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
    return Response(content=f[1], media_type="image/jpeg", headers={"Cache-Control": "no-store"})
