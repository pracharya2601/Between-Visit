import asyncio
import base64
import io
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import List, Literal, Optional

from emergentintegrations.llm.chat import ImageContent, LlmChat, StreamDone, TextDelta, UserMessage
from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from db import db
from models import Attempt, AttemptEvent
from sensors import sensors_for

logger = logging.getLogger(__name__)

MIN_INTERVAL_S = 1.0
TIMEOUT_S = 8.0
TIME_LIMIT_S = 30 * 60
SEND_WIDTH = 768
PERSON = re.compile(r"\b(person|people|man|men|woman|women|boy|girl|child|children|kid|pedestrian|someone|guy|lady|human)\b", re.I)

SYSTEM = (
    "You analyse one camera frame from a blind or low-vision traveller practising a known route with an "
    "orientation-and-mobility specialist. You reply with a single JSON object and nothing else."
)


class Entity(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    relation: Literal["left", "right", "ahead"]
    distance_band: Literal["near", "mid", "far"]
    confidence: float = Field(ge=0, le=1)


class VisionResult(BaseModel):
    checkpoint_match: Optional[str]
    on_route: bool
    new_entities: List[Entity]
    uncertain: bool
    unusable: bool


@dataclass
class Slot:
    frame: Optional[bytes] = None
    source: str = "glasses"
    in_flight: bool = False
    last_start: float = 0.0
    task: Optional[asyncio.Task] = None
    stopped: bool = False
    injected: bool = False


SLOTS: dict = {}


def offer(attempt_id: str, frame: bytes, source: str):
    """Keeps only the newest frame; frames arriving during a call are discarded (no queue)."""
    slot = SLOTS.setdefault(attempt_id, Slot())
    if slot.in_flight or slot.stopped or slot.injected:
        return
    slot.frame, slot.source = frame, source
    if slot.task is None:
        slot.task = asyncio.create_task(_drain(attempt_id, slot))


async def _drain(attempt_id: str, slot: Slot):
    try:
        wait = slot.last_start + MIN_INTERVAL_S - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        frame, source, slot.frame = slot.frame, slot.source, None
        if frame is None:
            return
        slot.in_flight = True
        slot.last_start = time.monotonic()
        try:
            await analyse(attempt_id, frame, source)
        except Exception:
            logger.exception("Vision worker failed")
        finally:
            slot.in_flight = False
            del frame
    finally:
        slot.task = None


def shrink(frame: bytes) -> bytes:
    img = Image.open(io.BytesIO(frame)).convert("RGB")
    if img.width > SEND_WIDTH:
        img = img.resize((SEND_WIDTH, max(1, round(img.height * SEND_WIDTH / img.width))))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=80)
    return out.getvalue()


def depth_line(snap: dict) -> str:
    vals = [snap["depth_left"], snap["depth_centre"], snap["depth_right"]]
    if all(v is None for v in vals):
        return "Depth unavailable: estimate distance_band from the image."
    left, centre, right = ("no reading" if v is None else f"{v:.2f}" for v in vals)
    return f"Depth (LiDAR, metres): left {left}, centre {centre}, right {right}. Use these for distance_band: near < 1.5, mid 1.5–4, far > 4."


def build_prompt(version: dict, last_match: Optional[str], depth_text: str) -> str:
    cps = sorted(version.get("checkpoints", []), key=lambda c: c["order"])
    cp_lines = "\n".join(f"{c['order']}. {c['name']}: {c['landmark_text']}" for c in cps) or "(none)"
    known = version.get("known_entities") or []
    known_lines = "\n".join(
        f"- {e.get('label')} (on the {e.get('side')}, between checkpoints {(e.get('segment') or {}).get('from')} and {(e.get('segment') or {}).get('to')}, verified by {e.get('verified_by')})" if isinstance(e, dict) else f"- {e}"
        for e in known
    ) or "(none)"
    return (
        f"Route memory (version {version.get('version')}).\n"
        f"Checkpoints in order (name: landmark):\n{cp_lines}\n"
        f"Known entities:\n{known_lines}\n"
        f"Last matched checkpoint: {last_match or 'none yet'}\n"
        f"{depth_text}\n\n"
        "Look at the frame. Reply with JSON only, no prose and no code fences, exactly this shape:\n"
        '{"checkpoint_match": <exact checkpoint name from the list, or null>, "on_route": <true|false>, '
        '"new_entities": [{"label": <short noun>, "relation": "left"|"right"|"ahead", "distance_band": "near"|"mid"|"far", "confidence": <0 to 1>}], '
        '"uncertain": <true|false>, "unusable": <true|false>}\n'
        "Rules:\n"
        "- checkpoint_match: the checkpoint whose landmark is clearly visible in this frame, using its exact name; otherwise null.\n"
        "- on_route: true if the scene fits this route near the last matched checkpoint or the next one.\n"
        "- new_entities: only objects that matter for walking (for example a chair, cart, sign stand or open door) that are not in the known entities. Use [] if there are none.\n"
        '- If a person is visible, use the label "person" only. Never describe a person.\n'
        "- uncertain: true if you are not sure about the match.\n"
        "- unusable: true if the frame is dark, blank, covered or too blurred to judge; then use checkpoint_match null and new_entities []."
    )


async def ask_model(model: str, prompt: str, jpeg: bytes) -> str:
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"vision-{uuid.uuid4()}", system_message=SYSTEM).with_model("anthropic", model)
    msg = UserMessage(text=prompt, file_contents=[ImageContent(image_base64=base64.b64encode(jpeg).decode())])
    parts = []
    async for ev in chat.stream_message(msg):
        if isinstance(ev, TextDelta):
            parts.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    return "".join(parts)


def parse_reply(reply: str, names: List[str]) -> Optional[VisionResult]:
    text = reply.strip()
    start, end = text.find("{"), text.rfind("}")
    try:
        result = VisionResult(**json.loads(text[start:end + 1] if start >= 0 else text))
    except (ValueError, TypeError, ValidationError):
        return None
    if result.checkpoint_match is not None:
        exact = {n.lower(): n for n in names}.get(result.checkpoint_match.strip().lower())
        if exact is None:
            result.checkpoint_match, result.uncertain = None, True
        else:
            result.checkpoint_match = exact
    for e in result.new_entities:
        if PERSON.search(e.label):
            e.label = "person"
    return result


async def log(attempt_id: str, type_: str, **fields) -> dict:
    doc = AttemptEvent(attempt_id=attempt_id, type=type_, **fields).to_mongo()
    await db.attempt_events.insert_one(dict(doc))
    return doc


async def log_and_cue(attempt_id: str, type_: str, snap: Optional[dict] = None, **fields):
    """Logs a vision/vision_error/vision_stopped event only if still running, then runs the relevance policy on it."""
    import cue_runner
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0, "status": 1})
    if not doc or doc["status"] != "running":
        return
    await cue_runner.handle(attempt_id, await log(attempt_id, type_, **fields), snap)


async def analyse(attempt_id: str, frame: bytes, source: str, timeout: float = TIMEOUT_S):
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not doc:
        return
    attempt = Attempt.from_mongo(doc)
    if attempt.status != "running":
        return
    if attempt.elapsed_seconds() > TIME_LIMIT_S:
        SLOTS.setdefault(attempt_id, Slot()).stopped = True
        if not await db.attempt_events.find_one({"attempt_id": attempt_id, "type": "vision_stopped"}):
            await log_and_cue(attempt_id, "vision_stopped", reason="time_limit")
        return
    ex = await db.exercises.find_one({"id": attempt.exercise_id}, {"_id": 0}) or {}
    version = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": attempt.route_version}, {"_id": 0}) or {}
    names = [c["name"] for c in version.get("checkpoints", [])]
    last = await db.attempt_events.find_one({"attempt_id": attempt_id, "type": "vision", "checkpoint": {"$ne": None}}, {"_id": 0, "checkpoint": 1}, sort=[("seq", -1)])
    model = os.environ["VISION_MODEL"]
    snap = sensors_for(attempt_id).snapshot()
    depth_text = depth_line(snap)
    t0 = time.monotonic()
    ms = lambda: int((time.monotonic() - t0) * 1000)  # noqa: E731
    try:
        jpeg = shrink(frame)
    except Exception:
        return await log_and_cue(attempt_id, "vision_error", reason="not_an_image", latency_ms=ms(), model=model, source=source)
    try:
        reply = await asyncio.wait_for(ask_model(model, build_prompt(version, last and last["checkpoint"], depth_text), jpeg), timeout)
    except asyncio.TimeoutError:
        return await log_and_cue(attempt_id, "vision_error", reason="timeout", latency_ms=ms(), model=model, source=source)
    except Exception as exc:
        return await log_and_cue(attempt_id, "vision_error", reason=f"call_failed: {type(exc).__name__}", latency_ms=ms(), model=model, source=source)
    result = parse_reply(reply, names)
    if result is None:
        return await log_and_cue(attempt_id, "vision_error", reason="bad_json", latency_ms=ms(), model=model, source=source)
    await log_and_cue(
        attempt_id, "vision", snap, result=result.model_dump(), latency_ms=ms(), model=model, route_version=version.get("version"),
        source=source, checkpoint=result.checkpoint_match, uncertain=result.uncertain, spoken=False,
        depth_prompt=depth_text, **snap,
    )
