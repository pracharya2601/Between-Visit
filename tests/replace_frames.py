"""Phase 16b: replace synthetic demo frames that showed a date stamp / camera UI, and the Hallway turn / Reception desk frames.
Keeps pose/depth metadata; runs both person checks; old blobs become unreferenced (unservable)."""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
from db import db  # noqa: E402
import recording  # noqa: E402
import vision_worker as vw  # noqa: E402
from storage import delete_object  # noqa: E402

NEW = {2: "f03.jpg", 4: "f05.jpg", 6: "f07.jpg", 7: "f08.jpg", 8: "f09.jpg", 10: "f11.jpg", 11: "f12.jpg"}


async def main():
    rec = await db.recordings.find_one({"kind": "synthetic"}, {"_id": 0})
    route = await db.routes.find_one({"id": rec["route_id"]}, {"_id": 0})
    v1 = await db.route_versions.find_one({"route_id": rec["route_id"], "version": 1}, {"_id": 0})
    names = [c["name"] for c in v1["checkpoints"]]
    frames, old = list(rec["frames"]), []
    for i, fname in NEW.items():
        jpeg = open(f"/root/frames_new/{fname}", "rb").read()
        f = frames[i]
        snap = {"pos_x": f["pose"]["x"], "pos_z": f["pose"]["z"], "heading_deg": f["pose"]["heading_deg"], "ar_tracking": f["pose"]["ar_tracking"],
                "depth_left": f["depth"]["left"], "depth_centre": f["depth"]["centre"], "depth_right": f["depth"]["right"]}
        reply = await vw.ask_model(os.environ["VISION_MODEL"], vw.build_prompt(v1, None, vw.depth_line(snap)), vw.shrink(jpeg), replay=True)
        result = vw.parse_reply(reply, names)
        reason = await recording.person_free(jpeg, result.model_dump() if result else None)
        print(f"frame {i + 1}: {'SKIP ' + reason if reason else 'passes both person checks'} | vision match {result and result.checkpoint_match} | {[e.label for e in (result.new_entities if result else [])]}")
        if reason:
            continue
        rel = f"recordings/{rec['id']}/{os.urandom(8).hex()}.jpg"
        res = await recording.put_object(rel, recording.strip_exif(jpeg), "image/jpeg")
        old.append(f["path"])
        frames[i] = {**f, "path": res.get("path") or f"{recording.APP_NAME}/{rel}"}
    await db.recordings.update_one({"id": rec["id"]}, {"$set": {"frames": frames}})
    print("route:", route["name"], "| frames:", len(frames))
    for p in old:
        print("old frame now unreferenced:", p, "(deleted)" if await delete_object(p) else "(storage has no delete; unservable)")


asyncio.run(main())
