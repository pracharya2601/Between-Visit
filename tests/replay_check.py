"""Phase 13 replay checks: synthetic replays on v1/v2, drift, public cap, 24 h sweep. Deletes its replay attempts afterwards."""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
API = os.environ["REACT_APP_BACKEND_URL"] + "/api"
ROUTE = "276dc5bb-53b0-4734-83d7-c7743052d09d"


def wait_end(aid, limit=90):
    t = time.time()
    while time.time() - t < limit:
        s = requests.get(f"{API}/replays/{aid}").json()
        if s["status"] == "ended":
            return s
        time.sleep(1)
    return s


async def chair_cues(aid):
    from db import db
    cues = await db.attempt_events.find({"attempt_id": aid, "type": "cue"}, {"_id": 0}).sort("seq", 1).to_list(500)
    chair = [(c.get("spoken"), c.get("suppressed_reason"), c.get("text")) for c in cues if "chair" in (str(c.get("entity") or "") + str(c.get("text") or "") + str(c.get("would_have_said") or "")).lower()]
    temp = await db.attempts.find_one({"id": aid}, {"_id": 0, "replay_fed_ms": 1})
    return chair, temp["replay_fed_ms"]


async def main():
    from db import db
    rec = await db.recordings.find_one({"route_id": ROUTE, "kind": "synthetic"}, {"_id": 0})
    offs = [f["t_offset_ms"] for f in rec["frames"]]
    made = []
    mode = sys.argv[1] if len(sys.argv) > 1 else "story"
    if mode == "story":
        for on in ("v1", "v1", "latest", "latest"):
            aid = requests.post(f"{API}/routes/{ROUTE}/replays", json={"on": on}).json()["attempt_id"]
            made.append(aid)
            s = wait_end(aid)
            chair, fed = await chair_cues(aid)
            drift = [f - o for f, o in zip(fed, offs)]
            print(f"== {on}: {s['version_line']} | spoken {s['cues_spoken']} held {s['cues_held_back']} | last cp {s['last_checkpoint']} | frames fed {len(fed)}/{len(offs)} | drift ms max {max(drift)} mean {sum(drift)/len(drift):.0f}")
            print("   chair cues:", chair)
    if mode == "cap":
        rs = [requests.post(f"{API}/demo/replays", json={"on": "latest"}) for _ in range(4)]
        print("== 4 public starts:", [r.status_code for r in rs], rs[-1].json())
        prac = requests.post(f"{API}/routes/{ROUTE}/replays", json={"on": "v1"})
        print("== practitioner replay while 3 public run:", prac.status_code)
        made += [r.json()["attempt_id"] for r in rs if r.status_code == 201] + [prac.json()["attempt_id"]]
        for aid in made:
            wait_end(aid)
        from replay import sweep_public_replays
        print("== sweep now:", await sweep_public_replays())
        print("== sweep +25 h:", await sweep_public_replays(datetime.now(timezone.utc) + timedelta(hours=25)))
        left = await db.attempts.count_documents({"id": {"$in": made}})
        print("== remaining of", len(made), "after sweep:", left, "(practitioner replay kept)")
    for aid in made:
        await db.attempt_events.delete_many({"attempt_id": aid})
        await db.attempts.delete_one({"id": aid})
    print("deleted check replays:", len(made))


asyncio.run(main())
