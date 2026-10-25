"""Phase 13 recording check: a tiny record_demo run with person frames mixed in, plus a normal run that must store nothing.
Afterwards the stored frames are made unservable (listed) and the check attempts/recording are deleted."""
import asyncio
import os
import sys
import time

import requests

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"] + "/api"
IMG = "https://static.prod-images.emergentagent.com/jobs/b64ebf54-447e-4e98-bd8c-1cc6c532d0bc/images/"
EMPTY = ["0693e790827ad295f3bb8c9cb9d83010f323d34431327a466c9565501bdb84b1", "5c434d4c044d22a082778fe579281fc5daa90b23147faab53b642a4605e21b51", "581243ed339462209c857a5d95dd43fb831ecf1e5df6b5e357bd6872c1cd4ed7"]
PERSON = ["22d831ac6ec371a1c754ea4026dd6d0961daf504a568d8069f8f93bba5f9633b", "07cdc5d33d7e7fe29bd2450e10b10f7f8581e44a2189ce3333558ccee4c05eda"]
ORDER = [("empty", EMPTY[0]), ("person", PERSON[0]), ("empty", EMPTY[1]), ("person", PERSON[1]), ("empty", EMPTY[2])]
EXERCISE = "6b0eb280-a8c7-414b-aee3-f7da0e719a9d"


def run(record: bool):
    r = requests.post(f"{API}/exercises/{EXERCISE}/attempts", json={"record_demo": record}).json()
    aid, key = r["attempt"]["id"], r["key"]
    h = {"X-Stream-Key": key}
    assert requests.get(f"{API}/run/{aid}", headers=h).json()["record_demo"] is record
    requests.post(f"{API}/run/{aid}/start", headers=h).raise_for_status()
    for kind, img in ORDER:
        jpeg = requests.get(IMG + img + ".jpeg", timeout=30).content
        code = requests.post(f"{API}/attempts/{aid}/frame", headers={**h, "Content-Type": "image/jpeg"}, data=jpeg).status_code
        print(f"   sent {kind} frame -> {code}")
        time.sleep(4)
    time.sleep(10)
    requests.post(f"{API}/run/{aid}/end", headers=h).raise_for_status()
    return aid


async def main():
    from db import db
    from storage import delete_object, get_object
    before = await db.recordings.count_documents({})
    print("== recorded run (record_demo=True), 3 empty + 2 person frames")
    rec_aid = run(True)
    print("== normal run (record_demo=False)")
    plain_aid = run(False)
    rec = await db.recordings.find_one({"attempt_id": rec_aid}, {"_id": 0})
    print("recording:", {k: rec[k] for k in ("kind", "label", "ready", "skipped")}, "frames stored:", len(rec["frames"]))
    for f in rec["frames"]:
        print("   frame", f["t_offset_ms"], "ms", f["source"], f["pose"], f["depth"])
    print("normal run recordings:", await db.recordings.count_documents({"attempt_id": plain_aid}), "| recordings before/after (excl. check):", before, await db.recordings.count_documents({}) - 1)
    jpeg = await get_object(rec["frames"][0]["path"]) if rec["frames"] else b""
    print("stored frame has EXIF:", b"Exif" in jpeg[:200])
    print("== making stored check frames unservable:")
    for f in rec["frames"]:
        print("   ", f["path"], "deleted" if await delete_object(f["path"]) else "delete not supported (unservable: record removed)")
    await db.recordings.delete_one({"id": rec["id"]})
    for aid in (rec_aid, plain_aid):
        await db.attempt_events.delete_many({"attempt_id": aid})
        await db.attempts.delete_one({"id": aid})
    print("deleted check attempts + recording")


asyncio.run(main())
