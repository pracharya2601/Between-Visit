"""Per-attempt policy state in memory, the 1 s timer, and delivery of spoken cues through the guide path."""
import asyncio
import logging
import time
from typing import Optional

import cue_policy
import ingest
from db import db
from models import Attempt, AttemptEvent

logger = logging.getLogger(__name__)

TIME_LIMIT_S = 30 * 60
STATES: dict = {}
CONTEXT: dict = {}
LOCKS: dict = {}
GENERATION: dict = {}


async def _context(attempt: Attempt):
    if attempt.id not in CONTEXT:
        ex = await db.exercises.find_one({"id": attempt.exercise_id}, {"_id": 0}) or {}
        version = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": ex.get("route_version")}, {"_id": 0}) or {}
        CONTEXT[attempt.id] = (ex, version)
    return CONTEXT[attempt.id]


async def _deliver(attempt_id: str, cue: cue_policy.Cue, event: dict):
    sent = await ingest.push_guide(attempt_id, cue.text, cue.priority) if cue.spoken else False
    fields = cue.as_dict()
    trigger = fields.pop("trigger")
    docs = [AttemptEvent(attempt_id=attempt_id, type="cue", reason=trigger, for_event_id=event.get("id"), **fields).to_mongo()]
    if cue.spoken:
        docs.append(AttemptEvent(attempt_id=attempt_id, type="guide", text=cue.text, priority=cue.priority, spoken=sent, reason="policy").to_mongo())
    await db.attempt_events.insert_many(docs)


async def handle(attempt_id: str, event: dict, sensors: Optional[dict] = None) -> Optional[Attempt]:
    """Runs the policy for one input on a running attempt; returns the attempt (None if missing)."""
    async with LOCKS.setdefault(attempt_id, asyncio.Lock()):
        doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
        if not doc:
            return None
        attempt = Attempt.from_mongo(doc)
        if attempt.status != "running":
            return attempt
        ex, version = await _context(attempt)
        snap = {**(sensors or {}), "last_frame_at": ingest.state_for(attempt_id).last_frame_at}
        cue, STATES[attempt_id] = cue_policy.decide(STATES.get(attempt_id, cue_policy.PolicyState()), event, ex, version, snap, time.time())
        if cue is not None:
            await _deliver(attempt_id, cue, event)
        return attempt


async def _timer(attempt_id: str, gen: int):
    while GENERATION.get(attempt_id) == gen:
        await asyncio.sleep(1)
        if GENERATION.get(attempt_id) != gen:
            return
        try:
            attempt = await handle(attempt_id, {"type": "tick"})
        except Exception:
            logger.exception("Cue timer failed")
            continue
        if attempt is None or attempt.status != "running" or attempt.elapsed_seconds() > TIME_LIMIT_S:
            GENERATION.pop(attempt_id, None)
            return


async def on_running(attempt_id: str):
    """Called on start/resume: re-arms the frame/result clocks and (re)starts the 1 s timer."""
    await handle(attempt_id, {"type": "running"})
    gen = GENERATION.get(attempt_id, 0) + 1
    GENERATION[attempt_id] = gen
    asyncio.create_task(_timer(attempt_id, gen))


def on_stopped(attempt_id: str, ended: bool):
    GENERATION.pop(attempt_id, None)
    if ended:
        for d in (STATES, CONTEXT, LOCKS):
            d.pop(attempt_id, None)


async def resume_running_timers():
    for doc in await db.attempts.find({"status": "running"}, {"_id": 0, "id": 1}).to_list(1000):
        await on_running(doc["id"])
