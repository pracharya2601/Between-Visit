"""One-time builder for the synthetic demo recording (AI-generated empty-corridor frames) on the 3D demo route."""
import asyncio
import os
import sys

import requests

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from db import db  # noqa: E402
from models import Recording  # noqa: E402
import recording  # noqa: E402
import vision_worker as vw  # noqa: E402

BASE = "https://static.prod-images.emergentagent.com/jobs/b64ebf54-447e-4e98-bd8c-1cc6c532d0bc/images/"
# (image, x, z, heading, depth left/centre/right)
FRAMES = [
    ("0693e790827ad295f3bb8c9cb9d83010f323d34431327a466c9565501bdb84b1", 0.0, 0.0, 0, (0.9, 9.6, 1.1)),
    ("203cf07d0b5c49c638bfa4523096418eef174976c2228894f02bad8e9c187c56", 0.0, -0.8, 0, (0.9, 8.8, 1.1)),
    ("afcda7ad415f6714d966da9d0a4b9c9602afc3d5887259c69eb1cffb5de7af77", 0.0, -1.9, 0, (0.9, 7.7, 3.1)),
    ("5c434d4c044d22a082778fe579281fc5daa90b23147faab53b642a4605e21b51", 0.0, -2.9, 0, (0.9, 2.1, 2.0)),
    ("cb8fd6ffa98739f5f6cb0533862d96b6b0f5070eba6f7b9386ba9fffa0f23855", 0.0, -3.8, 0, (0.9, 1.2, 1.0)),
    ("9f62114fc0b1372343972e5dd8b5d797bf2074acf6e15d300f41dc4b5291c39f", 0.0, -5.6, 0, (0.9, 4.3, 1.1)),
    ("bdc3092be9d5d8cc54f819080094e1ef08dff86a9d0881b33d0beee7e163d65f", 0.0, -8.4, 0, (0.9, 1.6, 3.5)),
    ("ba5e4c7b18277cbee2979e5d5857edef99f32c79fe973affdf974a95cda0fdde", 0.0, -9.9, 45, (0.8, 0.9, 3.2)),
    ("581243ed339462209c857a5d95dd43fb831ecf1e5df6b5e357bd6872c1cd4ed7", 1.4, -10.0, 90, (0.9, 4.6, 1.1)),
    ("7a5abdeed1b9b10d82076ce2bc3c5a94a0d1bdea12ce1a58992843052c5f38e8", 2.9, -10.0, 90, (0.9, 3.1, 1.1)),
    ("493d12f98d3b9ee48dd2e517f28b1fb366eb333cb69097cb3c8906dc34a68942", 4.3, -10.0, 90, (0.9, 1.8, 1.1)),
    ("a6d34bbfe8a09cb3afa8c32e9ada3f1ec9a1419e3f02621fe53a41bfc61a4370", 6.0, -10.0, 90, (0.8, 0.6, 0.9)),
]
GAP_MS = 1400


async def main():
    route = await db.routes.find_one({"name": "Entrance → hallway turn → reception desk (synthetic)"}, {"_id": 0})
    if await db.recordings.find_one({"route_id": route["id"], "kind": "synthetic", "ready": True}):
        print("synthetic recording already present")
        return
    ex = await db.exercises.find_one({"route_id": route["id"]}, {"_id": 0})
    v1 = await db.route_versions.find_one({"route_id": route["id"], "version": 1}, {"_id": 0})
    names = [c["name"] for c in v1["checkpoints"]]
    rec = Recording(route_id=route["id"], route_version=1, exercise_id=ex["id"], kind="synthetic", label=recording.SYNTHETIC_LABEL)
    await db.recordings.insert_one(rec.to_mongo())
    t = 0
    for i, (img, x, z, heading, (dl, dc, dr)) in enumerate(FRAMES):
        jpeg = requests.get(BASE + img + ".jpeg", timeout=30).content
        snap = {"pos_x": x, "pos_z": z, "heading_deg": heading, "ar_tracking": "normal", "depth_left": dl, "depth_centre": dc, "depth_right": dr}
        reply = await vw.ask_model(os.environ["VISION_MODEL"], vw.build_prompt(v1, None, vw.depth_line(snap)), vw.shrink(jpeg), replay=True)
        result = vw.parse_reply(reply, names)
        reason = await recording.person_free(jpeg, result.model_dump() if result else None)
        print(i, "skip: " + reason if reason else "stored", [e.label for e in (result.new_entities if result else [])], result and result.checkpoint_match)
        if not reason:
            await recording.store_frame(rec.id, jpeg, t, snap, "glasses")
            t += GAP_MS
    await db.recordings.update_one({"id": rec.id}, {"$set": {"ready": True}})
    doc = await db.recordings.find_one({"id": rec.id}, {"_id": 0})
    print("frames stored:", len(doc["frames"]))


asyncio.run(main())
