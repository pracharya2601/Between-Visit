"""Demo recordings: team-only recorded runs (fail-closed person checks) and the synthetic fallback. A narrow exception to 'never store frames'."""
import asyncio
import io
import logging
import uuid
from typing import Optional

from PIL import Image

from db import db
from models import Attempt, Recording
from storage import APP_NAME, put_object
from vision import process_image, suggest_landmark

logger = logging.getLogger(__name__)
TASKS: set = set()
SYNTHETIC_LABEL = "Synthetic demo (AI-generated images)"


def strip_exif(jpeg: bytes) -> bytes:
    out = io.BytesIO()
    Image.open(io.BytesIO(jpeg)).convert("RGB").save(out, "JPEG", quality=90)
    return out.getvalue()


async def person_free(jpeg: bytes, result: Optional[dict]) -> Optional[str]:
    """None when both person checks pass; otherwise the reason the frame must not be stored (fail closed)."""
    if result is None or any(e.get("label") == "person" for e in result.get("new_entities") or []):
        return "person_in_vision_result"
    try:
        status, _ = await suggest_landmark(process_image(jpeg)[0])
    except Exception:
        return "person_check_failed"
    return None if status == "suggested" else ("person_check_found_person" if status == "retake" else "person_check_failed")


async def store_frame(rec_id: str, jpeg: bytes, t_offset_ms: int, snap: dict, source: str) -> dict:
    rel = f"recordings/{rec_id}/{uuid.uuid4()}.jpg"
    res = await put_object(rel, strip_exif(jpeg), "image/jpeg")
    path = res.get("path") or f"{APP_NAME}/{rel}"
    frame = {"path": path, "t_offset_ms": t_offset_ms, "source": source,
             "pose": {"x": snap.get("pos_x"), "z": snap.get("pos_z"), "heading_deg": snap.get("heading_deg"), "ar_tracking": snap.get("ar_tracking")},
             "depth": {"left": snap.get("depth_left"), "centre": snap.get("depth_centre"), "right": snap.get("depth_right")}}
    await db.recordings.update_one({"id": rec_id}, {"$push": {"frames": frame}})
    return frame


async def _consider(attempt: Attempt, jpeg: bytes, result: dict, snap: dict, source: str, t_offset_ms: int):
    rec = await db.recordings.find_one({"attempt_id": attempt.id}, {"_id": 0, "id": 1})
    if not rec:
        ex = await db.exercises.find_one({"id": attempt.exercise_id}, {"_id": 0, "route_id": 1})
        doc = Recording(route_id=ex["route_id"], route_version=attempt.route_version, attempt_id=attempt.id, exercise_id=attempt.exercise_id, kind="real",
                        label=f"Recorded run {attempt.stream_id}").to_mongo()
        await db.recordings.update_one({"attempt_id": attempt.id}, {"$setOnInsert": doc}, upsert=True)
        rec = await db.recordings.find_one({"attempt_id": attempt.id}, {"_id": 0, "id": 1})
    reason = await person_free(jpeg, result)
    if reason:
        await db.recordings.update_one({"id": rec["id"]}, {"$inc": {f"skipped.{reason}": 1}})
        return
    await store_frame(rec["id"], jpeg, t_offset_ms, snap, source)


def consider(attempt: Attempt, jpeg: bytes, result: dict, snap: dict, source: str):
    """Called only for analysed frames of record_demo attempts; never for normal runs or replays."""
    assert attempt.record_demo and not attempt.replay, "frames are only stored for record_demo runs"
    t = asyncio.create_task(_consider(attempt, jpeg, result, snap, source, int(attempt.elapsed_seconds() * 1000)))
    TASKS.add(t)
    t.add_done_callback(lambda task: (TASKS.discard(task), task.exception() and logger.warning("Recording frame failed: %s", type(task.exception()).__name__)))


async def on_ended(attempt_id: str):
    await db.recordings.update_one({"attempt_id": attempt_id, "frames.0": {"$exists": True}}, {"$set": {"ready": True}})
