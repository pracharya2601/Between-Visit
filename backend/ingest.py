import asyncio
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException, Request, WebSocket
from pydantic import BaseModel, StringConstraints, ValidationError

import sensors
import vision_worker
from db import db
from models import Attempt

MAX_FRAME_BYTES = 1024 * 1024
TEST_STREAM_ID = "att-test"

router = APIRouter(prefix="/api")


class HideIngestSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/api/ws/ingest" not in msg and "key=" not in msg


def install_log_filter():
    for name in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).addFilter(HideIngestSecrets())


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def key_matches(key: Optional[str], key_hash: str) -> bool:
    return bool(key) and hmac.compare_digest(hash_key(key), key_hash)


@dataclass
class StreamState:
    ws: Optional[WebSocket] = None
    frames_received: int = 0
    frames_dropped: int = 0
    last_frame_at: Optional[float] = None
    last_frame_size: Optional[int] = None
    held_motion: Optional[dict] = None
    last_motion: Optional[dict] = None
    glasses_frames: int = 0
    phone_frames: int = 0
    last_glasses_frame_at: Optional[float] = None
    last_phone_frame_at: Optional[float] = None

    def accept_frame(self, size: int, motion: Optional[dict] = None, src: str = "glasses"):
        self.frames_received += 1
        self.last_frame_at = time.time()
        self.last_frame_size = size
        if src == "glasses":
            self.glasses_frames += 1
            self.last_glasses_frame_at = self.last_frame_at
        else:
            self.phone_frames += 1
            self.last_phone_frame_at = self.last_frame_at
        motion = motion or self.held_motion
        if motion is not None:
            self.last_motion = motion
        self.held_motion = None

    def seconds_since_glasses_frame(self) -> Optional[float]:
        return round(time.time() - self.last_glasses_frame_at, 1) if self.last_glasses_frame_at else None


STREAMS: Dict[str, StreamState] = {}


def state_for(attempt_id: str) -> StreamState:
    return STREAMS.setdefault(attempt_id, StreamState())


async def push_guide(attempt_id: str, text: str, priority: int = 1) -> bool:
    ws = state_for(attempt_id).ws
    if ws is None:
        return False
    try:
        await asyncio.wait_for(ws.send_json({"type": "guide", "text": text, "priority": priority, "speak": True}), 2)
        return True
    except Exception:
        return False


class Motion(BaseModel):
    type: Literal["motion"]
    ts_ns: int
    q: List[float]
    acc: List[float]
    gyro: List[float]
    mag: List[float]
    src: str


class CueIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=199)]
    priority: Literal[0, 1, 2] = 1


class StreamStatus(BaseModel):
    live: bool
    frames_received: int
    frames_dropped: int
    seconds_since_last_frame: Optional[float]
    last_frame_size: Optional[int]
    last_motion: Optional[Dict[str, Any]]
    glasses_frames: int
    phone_frames: int
    seconds_since_glasses_frame: Optional[float]
    pose_x: Optional[float]
    pose_z: Optional[float]
    heading_deg: Optional[float]
    ar_tracking: Optional[str]
    has_lidar: Optional[bool]
    depth_left: Optional[float]
    depth_centre: Optional[float]
    depth_right: Optional[float]
    depth_frames_received: int
    depth_dropped: int
    depth_unpaired: int


async def find_attempt(**query) -> Optional[Attempt]:
    doc = await db.attempts.find_one(query, {"_id": 0})
    return Attempt.from_mongo(doc) if doc else None


async def require_attempt(attempt_id: str) -> Attempt:
    attempt = await find_attempt(id=attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


def parse_json(text: str) -> dict:
    try:
        obj = json.loads(text)
    except ValueError:
        return {}
    return obj if isinstance(obj, dict) else {}


def parse_motion(obj: dict) -> Optional[dict]:
    try:
        return Motion(**obj).model_dump()
    except (ValueError, TypeError, ValidationError):
        return None


async def take_over(state: StreamState, ws: WebSocket):
    old, state.ws = state.ws, ws
    if old is not None:
        try:
            await old.close(code=1000, reason="Replaced by a new connection")
        except Exception:
            pass


@router.websocket("/ws/ingest/{stream_id}")
async def ingest(ws: WebSocket, stream_id: str):
    await ws.accept()
    attempt = await find_attempt(stream_id=stream_id)
    if not attempt or not key_matches(ws.query_params.get("key"), attempt.key_hash):
        await ws.close(code=1008)
        return
    state = state_for(attempt.id)
    await take_over(state, ws)
    await ws.send_json({"viewers": 0})
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data is not None:
                if data[:4] == sensors.DEPTH_MAGIC:
                    sensors.on_depth(attempt.id, data)
                elif len(data) > MAX_FRAME_BYTES:
                    state.frames_dropped += 1
                else:
                    state.accept_frame(len(data))
                    vision_worker.offer(attempt.id, data, "glasses")
                continue
            obj = parse_json(msg.get("text") or "")
            if obj.get("type") == "phone":
                sensors.on_phone_line(attempt.id, obj)
                continue
            motion = parse_motion(obj)
            if motion:
                state.held_motion = motion
    except Exception:
        pass
    finally:
        if state.ws is ws:
            state.ws = None


@router.post("/attempts/{attempt_id}/frame", status_code=202)
async def phone_frame(
    attempt_id: str,
    request: Request,
    heading: Optional[float] = None,
    steps: Optional[int] = None,
    x_stream_key: Optional[str] = Header(default=None),
):
    attempt = await require_attempt(attempt_id)
    if not key_matches(x_stream_key, attempt.key_hash):
        raise HTTPException(status_code=401, detail="Invalid stream key")
    state = state_for(attempt.id)
    size = 0
    body = bytearray()
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_FRAME_BYTES:
            state.frames_dropped += 1
            raise HTTPException(status_code=413, detail="Frame over 1 MB")
        body.extend(chunk)
    if size == 0:
        raise HTTPException(status_code=422, detail="Empty frame")
    state.accept_frame(size, {"src": "phone", "heading": heading, "steps": steps}, src="phone")
    vision_worker.offer(attempt.id, bytes(body), "phone")
    return {"accepted": True, "frames_received": state.frames_received}


@router.get("/attempts/{attempt_id}/status", response_model=StreamStatus)
async def stream_status(attempt_id: str):
    await require_attempt(attempt_id)
    s = state_for(attempt_id)
    sn = sensors.sensors_for(attempt_id)
    x, z = sn.pose_xz()
    depth = sn.depth or {}
    since = round(time.time() - s.last_frame_at, 1) if s.last_frame_at else None
    return StreamStatus(
        live=s.ws is not None,
        frames_received=s.frames_received,
        frames_dropped=s.frames_dropped,
        seconds_since_last_frame=since,
        last_frame_size=s.last_frame_size,
        last_motion=s.last_motion,
        glasses_frames=s.glasses_frames,
        phone_frames=s.phone_frames,
        seconds_since_glasses_frame=s.seconds_since_glasses_frame(),
        pose_x=x,
        pose_z=z,
        heading_deg=sn.phone.get("heading_deg"),
        ar_tracking=sn.phone.get("ar_tracking"),
        has_lidar=sn.phone.get("has_lidar"),
        depth_left=depth.get("left"),
        depth_centre=depth.get("centre"),
        depth_right=depth.get("right"),
        depth_frames_received=sn.depth_frames_received,
        depth_dropped=sn.depth_dropped,
        depth_unpaired=sn.depth_unpaired,
    )


@router.post("/attempts/{attempt_id}/cue")
async def send_cue(attempt_id: str, cue: CueIn):
    await require_attempt(attempt_id)
    if not await push_guide(attempt_id, cue.text, cue.priority):
        raise HTTPException(status_code=409, detail="Not connected")
    return {"sent": True}


@router.get("/device-test/config")
async def device_test_config():
    doc = await db.test_config.find_one({"stream_id": TEST_STREAM_ID}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Test attempt not seeded")
    return {"stream_id": doc["stream_id"], "attempt_id": doc["attempt_id"], "key": doc["key"]}
