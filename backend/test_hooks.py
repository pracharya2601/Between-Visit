"""Check-only vision injection. Mounted only when CUE_TEST_HOOK=1; unreachable in normal use."""
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import cue_runner
import vision_worker
from db import db
from sensors import sensors_for

router = APIRouter(prefix="/api/test-hooks")


class InjectIn(BaseModel):
    type: Literal["vision", "vision_error"] = "vision"
    result: Optional[vision_worker.VisionResult] = None


@router.post("/attempts/{attempt_id}/vision")
async def inject_vision(attempt_id: str, body: InjectIn):
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0, "status": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Attempt not found")
    vision_worker.SLOTS.setdefault(attempt_id, vision_worker.Slot()).injected = True
    if doc["status"] != "running":
        return {"logged": False}
    snap = sensors_for(attempt_id).snapshot()
    if body.type == "vision_error":
        ev = await vision_worker.log(attempt_id, "vision_error", reason="injected", model="injected")
    else:
        result = body.result.model_dump()
        ev = await vision_worker.log(attempt_id, "vision", result=result, model="injected", checkpoint=result["checkpoint_match"], uncertain=result["uncertain"], **snap)
    await cue_runner.handle(attempt_id, ev, snap)
    return {"logged": True, "event_id": ev["id"], "seq": ev["seq"]}
