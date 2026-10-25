"""Phase 13 follow-up: second person check decision, fail-closed paths, and sweep keeps public replays with a correction. Stores nothing."""
import asyncio
import sys
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
import recording  # noqa: E402
import vision  # noqa: E402

IMG = "https://static.prod-images.emergentagent.com/jobs/b64ebf54-447e-4e98-bd8c-1cc6c532d0bc/images/"
PERSONS = ["22d831ac6ec371a1c754ea4026dd6d0961daf504a568d8069f8f93bba5f9633b", "07cdc5d33d7e7fe29bd2450e10b10f7f8581e44a2189ce3333558ccee4c05eda"]
NO_PERSON = {"checkpoint_match": None, "on_route": True, "new_entities": [{"label": "door", "relation": "ahead", "distance_band": "far", "confidence": 0.9}], "uncertain": False, "unusable": False}


def stored_never(*_a, **_k):
    raise AssertionError("store_frame must not be called")


async def main():
    from db import db
    from models import Attempt, AttemptEvent, Correction
    from replay import sweep_public_replays
    recording.store_frame = stored_never
    for i, img in enumerate(PERSONS, 1):
        jpeg = requests.get(IMG + img + ".jpeg", timeout=30).content
        print(f"person image {i}, vision result without person -> decision:", await recording.person_free(jpeg, NO_PERSON) or "STORE")
    jpeg = requests.get(IMG + PERSONS[0] + ".jpeg", timeout=30).content
    real_ask, real_timeout = vision._ask_claude, vision.AI_TIMEOUT_S

    async def slow(_):
        await asyncio.sleep(5)
        return "A corridor."
    vision._ask_claude, vision.AI_TIMEOUT_S = slow, 0.5
    print("forced Sonnet timeout -> decision:", await recording.person_free(jpeg, NO_PERSON) or "STORE")

    async def boom(_):
        raise RuntimeError("forced failure")
    vision._ask_claude = boom
    print("forced Sonnet failure -> decision:", await recording.person_free(jpeg, NO_PERSON) or "STORE")
    vision._ask_claude, vision.AI_TIMEOUT_S = real_ask, real_timeout

    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    ids = []
    for with_corr in (True, False):
        a = Attempt(exercise_id="6b0eb280-a8c7-414b-aee3-f7da0e719a9d", status="ended", stream_id=f"att-chk{int(with_corr)}", key_hash="x", route_version=1, replay=True, public=True, recording_id="none", created_at=old)
        await db.attempts.insert_one(a.to_mongo())
        ev = AttemptEvent(attempt_id=a.id, type="cue", text="Chair ahead.")
        await db.attempt_events.insert_one(ev.to_mongo())
        if with_corr:
            c = Correction(attempt_event_id=ev.id, action="dismiss", author="check")
            await db.corrections.insert_one({**c.to_mongo(), **{k: v for k, v in {}.items()}})
            corr_id = c.id
        ids.append(a.id)
    n = await sweep_public_replays(datetime.now(timezone.utc) + timedelta(hours=25))
    kept = await db.attempts.find_one({"id": ids[0]}) is not None
    control = await db.attempts.find_one({"id": ids[1]}) is not None
    print(f"sweep +25h deleted {n} | public replay with correction kept: {kept} | control without correction kept: {control}")
    await db.corrections.delete_one({"id": corr_id})
    await db.attempt_events.delete_many({"attempt_id": {"$in": ids}})
    await db.attempts.delete_many({"id": {"$in": ids}})
    print("cleanup: replays", await db.attempts.count_documents({"replay": True}), "| corrections", await db.corrections.count_documents({}),
          "| recordings", [(r["kind"], len(r["frames"])) for r in await db.recordings.find({}, {"_id": 0}).to_list(10)])


asyncio.run(main())
