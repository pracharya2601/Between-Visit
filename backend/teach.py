import asyncio
import json
import logging
import math
import secrets
import string
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Annotated, Deque, List, Literal, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Response, WebSocket
from pydantic import BaseModel, Field, StringConstraints, ValidationError
from pymongo.errors import DuplicateKeyError

import sensors
from db import db
from ingest import MAX_FRAME_BYTES, hash_key, key_matches, parse_json, state_for, take_over
from migrations import delete_routes_cascade
from models import Checkpoint, Route, RouteMemory, TeachSession, now_iso
from storage import put_object
from vision import process_image, suggest_landmark
from workspace import attach_photo, create_version, route_checkpoints

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

VOXEL_M = 0.05
MAX_POINTS = 200_000
BROWSER_POINTS = 50_000
TRAIL_STEP_M = 0.25
TURN_WINDOW_M = 2.0
TURN_DEG = 45.0
MIN_GAP_M = 2.0
RING_S = 3.0
PICK_WINDOW_S = 1.0
MAX_CANDIDATES = 5
IDLE_EXPIRY_S = 2 * 3600
ALPHABET = string.ascii_lowercase + string.digits

Floats16 = Annotated[List[float], Field(min_length=16, max_length=16)]


class Plane(BaseModel):
    id: str
    align: Literal["horizontal", "vertical"]
    cls: Literal["floor", "wall", "ceiling", "table", "seat", "door", "window", "none"] = Field(alias="class")
    transform: Floats16
    center: Annotated[List[float], Field(min_length=3, max_length=3)]
    extent: Annotated[List[float], Field(min_length=2, max_length=2)]
    rotation_y: float
    polygon: Annotated[List[Annotated[List[float], Field(min_length=2, max_length=2)]], Field(max_length=32)] = []


@dataclass
class TeachMap:
    keys: set = field(default_factory=set)
    points: list = field(default_factory=list)
    planes: list = field(default_factory=list)
    trail: list = field(default_factory=list)
    cum: list = field(default_factory=list)
    proposals: list = field(default_factory=list)
    turns: int = 0
    limit_reached: bool = False
    ring: Deque[tuple] = field(default_factory=deque)
    last_activity: float = field(default_factory=time.time)
    last_db_touch: float = 0.0
    tasks: set = field(default_factory=set)
    finished: bool = False


MAPS: dict = {}
ATTEMPT_TRAIL_LAST: dict = {}


def map_for(session_id: str) -> TeachMap:
    return MAPS.setdefault(session_id, TeachMap())


def add_points(m: TeachMap, arr: np.ndarray, intr, pose) -> None:
    fx, fy, cx, cy = intr
    sub = arr[::8, ::8].astype(np.float64) / 1000.0
    vv, uu = np.mgrid[0:arr.shape[0]:8, 0:arr.shape[1]:8]
    mask = sub > 0
    d, u, v = sub[mask], uu[mask], vv[mask]
    x_right = (u + 0.5 - cx) / fx * d
    y_up = -(v + 0.5 - cy) / fy * d
    cam = np.vstack([-y_up, x_right, -d, np.ones_like(d)])
    world = (np.asarray(pose, dtype=np.float64).reshape(4, 4, order="F") @ cam)[:3].T
    k = np.floor(world / VOXEL_M).astype(np.int64) + (1 << 20)
    packed = (k[:, 0] << 42) | (k[:, 1] << 21) | k[:, 2]
    for key, p in zip(packed.tolist(), world.tolist()):
        if len(m.points) >= MAX_POINTS:
            m.limit_reached = True
            return
        if key not in m.keys:
            m.keys.add(key)
            m.points.append(p)


def parse_planes(raw) -> Optional[list]:
    if not isinstance(raw, list):
        return None
    planes = []
    for item in raw[:32]:
        try:
            planes.append(Plane(**item).model_dump(by_alias=True))
        except (TypeError, ValidationError):
            continue
    return planes


def _xz_angle(a, b) -> float:
    dot = a[0] * b[0] + a[1] * b[1]
    n = math.hypot(*a) * math.hypot(*b)
    return 0.0 if n == 0 else math.degrees(math.acos(max(-1.0, min(1.0, dot / n))))


def turn_corner(m: TeachMap) -> Optional[int]:
    """Index of the corner if walking direction changed >45° within ~2 m windows, else None."""
    n = len(m.trail) - 1
    a = next((i for i in range(n, -1, -1) if m.cum[n] - m.cum[i] >= TURN_WINDOW_M), None)
    if a is None:
        return None
    b = next((i for i in range(a, -1, -1) if m.cum[a] - m.cum[i] >= TURN_WINDOW_M), None)
    if b is None:
        return None
    P, A, B = m.trail[n], m.trail[a], m.trail[b]
    if _xz_angle((A[0] - B[0], A[2] - B[2]), (P[0] - A[0], P[2] - A[2])) <= TURN_DEG:
        return None
    dx, dz = P[0] - B[0], P[2] - B[2]
    length = math.hypot(dx, dz) or 1.0
    return max(range(b, n + 1), key=lambda i: abs((m.trail[i][0] - B[0]) * dz - (m.trail[i][2] - B[2]) * dx) / length)


async def pick_photo(cp_id: str, candidates: list):
    for frame in candidates:
        try:
            jpeg, w, h = process_image(frame)
        except ValueError:
            continue
        status, text = await suggest_landmark(jpeg)
        if status == "retake":
            continue
        try:
            await attach_photo(cp_id, jpeg, w, h, status, text)
            return
        except Exception:
            logger.warning("Teach photo store failed")
            break
    await db.checkpoints.update_one({"id": cp_id}, {"$set": {"needs_photo": True, "photo_pending": False}})


async def propose(session: TeachSession, m: TeachMap, name: str, point) -> None:
    x, y, z, t = point
    m.proposals.append((x, z))
    order = await db.checkpoints.count_documents({"route_id": session.route_id}) + 1
    cp = Checkpoint(route_id=session.route_id, order=order, name=name, position=[x, y, z], photo_pending=True)
    await db.checkpoints.insert_one(cp.to_mongo())
    task = asyncio.create_task(pick_later(m, cp.id, t))
    m.tasks.add(task)
    task.add_done_callback(m.tasks.discard)


async def pick_later(m: TeachMap, cp_id: str, t: float):
    """Waits until frames up to 1 s after the checkpoint time are buffered, then picks the nearest person-free one."""
    await asyncio.sleep(max(0.0, t + PICK_WINDOW_S - time.time()))
    near = sorted((f for f in m.ring if abs(f[0] - t) <= PICK_WINDOW_S), key=lambda f: abs(f[0] - t))
    candidates = [f[1] for f in near[:MAX_CANDIDATES]]
    if m.finished:
        m.ring.clear()
    await pick_photo(cp_id, candidates)


def far_from_proposals(m: TeachMap, x: float, z: float) -> bool:
    return all(math.hypot(x - px, z - pz) >= MIN_GAP_M for px, pz in m.proposals)


async def on_teach_phone(session: TeachSession, m: TeachMap, obj: dict):
    planes = parse_planes(obj.get("ar_planes")) if "ar_planes" in obj else None
    if planes is not None:
        m.planes = planes
    pose = obj.get("ar_pose")
    if obj.get("ar_tracking") != "normal" or not sensors.PHONE_FIELDS["ar_pose"](pose):
        return
    p = (pose[12], pose[13], pose[14], time.time())
    if m.trail:
        step = math.dist(p[:3], m.trail[-1][:3])
        if step < TRAIL_STEP_M:
            return
        m.trail.append(p)
        m.cum.append(m.cum[-1] + step)
    else:
        m.trail.append(p)
        m.cum.append(0.0)
        return await propose(session, m, "Start", p)
    corner = turn_corner(m)
    if corner is not None and far_from_proposals(m, m.trail[corner][0], m.trail[corner][2]):
        m.turns += 1
        await propose(session, m, f"Turn {m.turns}", m.trail[corner])


async def touch(session: TeachSession, m: TeachMap):
    m.last_activity = time.time()
    if m.last_activity - m.last_db_touch > 60:
        m.last_db_touch = m.last_activity
        await db.teach_sessions.update_one({"id": session.id}, {"$set": {"updated_at": now_iso()}})


async def ingest_teach(ws: WebSocket, stream_id: str):
    doc = await db.teach_sessions.find_one({"stream_id": stream_id, "status": "active"}, {"_id": 0})
    if not doc or not key_matches(ws.query_params.get("key"), doc["key_hash"]):
        await ws.close(code=1008)
        return
    session = TeachSession.from_mongo(doc)
    state, m = state_for(session.id), map_for(session.id)
    await take_over(state, ws)
    await ws.send_json({"viewers": 0})
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            await touch(session, m)
            data = msg.get("bytes")
            if data is not None:
                if data[:4] == sensors.DEPTH_MAGIC:
                    paired = sensors.on_depth(session.id, data)
                    if paired and paired[3] == "normal" and paired[2] and not m.limit_reached:
                        add_points(m, paired[0], paired[1], paired[2])
                elif len(data) > MAX_FRAME_BYTES:
                    state.frames_dropped += 1
                else:
                    state.accept_frame(len(data))
                    now = time.time()
                    m.ring.append((now, data))
                    while m.ring and now - m.ring[0][0] > RING_S:
                        m.ring.popleft()
                continue
            obj = parse_json(msg.get("text") or "")
            if obj.get("type") == "phone":
                sensors.on_phone_line(session.id, obj)
                await on_teach_phone(session, m, obj)
    except Exception:
        logger.exception("Teach ingest stopped")
    finally:
        if state.ws is ws:
            state.ws = None


async def attempt_trail(attempt_id: str, obj: dict):
    """Client runs: store a practitioner-only trail point every 0.25 m while running (ar_planes ignored)."""
    pose = obj.get("ar_pose")
    if not sensors.PHONE_FIELDS["ar_pose"](pose):
        return
    x, z = pose[12], pose[14]
    last = ATTEMPT_TRAIL_LAST.get(attempt_id)
    if last and math.hypot(x - last[0], z - last[1]) < TRAIL_STEP_M:
        return
    res = await db.attempts.update_one({"id": attempt_id, "status": "running"}, {"$push": {"trail": {"x": x, "z": z, "t": now_iso()}}})
    if res.modified_count:
        ATTEMPT_TRAIL_LAST[attempt_id] = (x, z)


async def end_session(session_id: str, status: str, discard_route: bool):
    for ws_state in (state_for(session_id),):
        if ws_state.ws is not None:
            try:
                await ws_state.ws.close(code=1000, reason="Teach session ended")
            except Exception:
                pass
    await db.teach_sessions.update_one({"id": session_id}, {"$set": {"status": status, "key": None, "updated_at": now_iso()}})
    if discard_route:
        m = MAPS.pop(session_id, None)
        for t in list(m.tasks if m else []):
            t.cancel()
        doc = await db.teach_sessions.find_one({"id": session_id}, {"_id": 0, "route_id": 1})
        await delete_routes_cascade([doc["route_id"]])


async def expire_idle_sessions():
    while True:
        try:
            cutoff = time.time() - IDLE_EXPIRY_S
            for doc in await db.teach_sessions.find({"status": "active"}, {"_id": 0, "id": 1, "updated_at": 1}).to_list(1000):
                last = max(MAPS[doc["id"]].last_activity if doc["id"] in MAPS else 0, _ts(doc["updated_at"]))
                if last < cutoff:
                    await end_session(doc["id"], "expired", discard_route=True)
        except Exception:
            logger.exception("Teach expiry check failed")
        await asyncio.sleep(60)


def _ts(iso: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso).timestamp()


class TeachIn(BaseModel):
    route_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TeachView(BaseModel):
    id: str
    route_name: str
    route_id: str
    stream_id: str
    status: str
    saved: bool
    key: Optional[str] = None


class TeachStatus(BaseModel):
    status: str
    live: bool
    metres_walked: float
    points: int
    point_limit_reached: bool
    planes: int
    checkpoints_proposed: int


async def get_session(session_id: str) -> TeachSession:
    doc = await db.teach_sessions.find_one({"id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Teach walk not found")
    return TeachSession.from_mongo(doc)


def view(s: TeachSession) -> TeachView:
    return TeachView(**s.model_dump(exclude={"key"}), key=s.key if s.status == "active" else None)


@router.post("/teach", response_model=TeachView, status_code=201)
async def start_teach(body: TeachIn):
    practice = await db.practices.find_one({}, {"_id": 0, "id": 1})
    route = Route(practice_id=practice["id"], name=body.route_name, teach_pending=True)
    key = secrets.token_urlsafe(24)
    for _ in range(20):
        stream_id = "tch-" + "".join(secrets.choice(ALPHABET) for _ in range(4))
        if await db.attempts.find_one({"stream_id": stream_id}):
            continue
        session = TeachSession(route_name=body.route_name, route_id=route.id, stream_id=stream_id, key_hash=hash_key(key), key=key)
        try:
            await db.teach_sessions.insert_one(session.to_mongo())
            break
        except DuplicateKeyError:
            continue
    else:
        raise HTTPException(status_code=503, detail="Couldn't create a unique stream ID. Try again.")
    await db.routes.insert_one(route.to_mongo())
    return view(session)


@router.get("/teach/{session_id}", response_model=TeachView)
async def teach_detail(session_id: str):
    return view(await get_session(session_id))


@router.get("/teach/{session_id}/status", response_model=TeachStatus)
async def teach_status(session_id: str):
    s = await get_session(session_id)
    m = MAPS.get(s.id) or TeachMap()
    return TeachStatus(
        status=s.status, live=state_for(s.id).ws is not None, metres_walked=round(m.cum[-1] if m.cum else 0.0, 2),
        points=len(m.points), point_limit_reached=m.limit_reached, planes=len(m.planes),
        checkpoints_proposed=await db.checkpoints.count_documents({"route_id": s.route_id}),
    )


@router.post("/teach/{session_id}/finish", response_model=TeachView)
async def finish_teach(session_id: str):
    s = await get_session(session_id)
    if s.status != "active":
        raise HTTPException(status_code=409, detail="This walk isn't active")
    m = map_for(s.id)
    m.finished = True
    if m.trail:
        await propose(s, m, "End", m.trail[-1])
    else:
        m.ring.clear()
    await end_session(s.id, "finished", discard_route=False)
    return view(await get_session(s.id))


@router.post("/teach/{session_id}/cancel", response_model=TeachView)
async def cancel_teach(session_id: str):
    s = await get_session(session_id)
    if s.saved or s.status in ("cancelled", "expired"):
        raise HTTPException(status_code=409, detail="This walk can't be cancelled")
    await end_session(s.id, "cancelled", discard_route=True)
    return view(await get_session(s.id))


def require_review(s: TeachSession) -> TeachMap:
    if s.status != "finished" or s.saved:
        raise HTTPException(status_code=409, detail="This walk isn't waiting for review")
    return MAPS.get(s.id) or TeachMap()


def require_live_or_review(s: TeachSession) -> TeachMap:
    """Points/scene are also readable while the walk is active (live map on the teach page)."""
    if s.status == "active":
        return MAPS.get(s.id) or TeachMap()
    return require_review(s)


def walker(session_id: str) -> Optional[dict]:
    snap = sensors.sensors_for(session_id).snapshot()
    pose = sensors.sensors_for(session_id).phone.get("ar_pose")
    if snap.get("pos_x") is None or not pose:
        return None
    return {"x": pose[12], "y": pose[13], "z": pose[14], "heading_deg": snap.get("heading_deg")}


@router.get("/teach/{session_id}/live-frame")
async def teach_live_frame(session_id: str):
    s = await get_session(session_id)
    m = MAPS.get(s.id)
    if s.status != "active" or not m or not m.ring:
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
    return Response(content=m.ring[-1][1], media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/teach/{session_id}/points")
async def teach_points(session_id: str):
    m = require_live_or_review(await get_session(session_id))
    pts = np.asarray(m.points, dtype="<f4").reshape(-1, 3)
    if len(pts) > BROWSER_POINTS:
        pts = pts[np.linspace(0, len(pts) - 1, BROWSER_POINTS).astype(np.int64)]
    return Response(content=pts.tobytes(), media_type="application/octet-stream", headers={"X-Point-Count": str(len(pts)), "Cache-Control": "no-store"})


@router.get("/teach/{session_id}/scene")
async def teach_scene(session_id: str):
    s = await get_session(session_id)
    m = require_live_or_review(s)
    cps = await route_checkpoints(s.route_id)
    return {"status": s.status, "walker": walker(s.id) if s.status == "active" else None,
        "points": len(m.points), "points_sent": min(len(m.points), BROWSER_POINTS), "metres_walked": round(m.cum[-1] if m.cum else 0.0, 2),
        "planes": m.planes, "trail": [p[:3] for p in m.trail],
        "checkpoints": [{"id": c.id, "order": c.order, "name": c.name, "position": c.position} for c in cps],
    }


@router.post("/teach/{session_id}/save")
async def save_teach(session_id: str):
    s = await get_session(session_id)
    m = require_review(s)
    route = Route.from_mongo(await db.routes.find_one({"id": s.route_id}, {"_id": 0}))
    cps = await route_checkpoints(route.id)
    if not cps:
        raise HTTPException(status_code=422, detail="Add at least one checkpoint")
    if not all(c.approved for c in cps):
        raise HTTPException(status_code=422, detail="Approve every checkpoint")
    memory_id = None
    if m.points or m.trail:
        pts = np.asarray(m.points, dtype="<f4").reshape(-1, 3).tobytes()
        meta = json.dumps({"planes": m.planes, "trail": m.trail, "metres_walked": m.cum[-1] if m.cum else 0.0}).encode()
        p1 = (await put_object(f"memory/{s.id}/points.f32", pts, "application/octet-stream"))["path"]
        p2 = (await put_object(f"memory/{s.id}/memory.json", meta, "application/json"))["path"]
        mem = RouteMemory(route_id=route.id, teach_session_id=s.id, points_path=p1, json_path=p2, point_count=len(m.points), plane_count=len(m.planes), trail_m=round(m.cum[-1] if m.cum else 0.0, 2))
        await db.route_memories.insert_one(mem.to_mongo())
        memory_id = mem.id
    version = await create_version(route, cps, memory_id)
    await db.routes.update_one({"id": route.id}, {"$set": {"teach_pending": False}})
    await db.teach_sessions.update_one({"id": s.id}, {"$set": {"saved": True, "key": None, "updated_at": now_iso()}})
    MAPS.pop(s.id, None)
    return {"version": version.version, "route_id": route.id, "memory_saved": memory_id is not None}


@router.get("/attempts/{attempt_id}/trail")
async def attempt_trail_view(attempt_id: str):
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0, "trail": 1})
    if doc is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return doc.get("trail", [])
