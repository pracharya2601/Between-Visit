"""Phase 20 simulated runs for Watch live, over the public wss (frames are never stored).
  python3 sim_live_run.py demo         demo taught route, recording frames + poses (vision + cues are real)
  python3 sim_live_run.py depth        temporary photo route (no 3D memory) with DPT1 depth -> live points
  python3 sim_live_run.py nodepth      the same route, poses only -> trail on a floor grid
  python3 sim_live_run.py cleanup      delete the temporary route / exercises / attempts
Env HOLD_S: seconds to wait between steps (screenshot time). State: /app/tests/.live_sim.json"""
import asyncio
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
import websockets

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/tests")
from teach_walk_sim import depth_frame, pose  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
WSS = API.replace("https://", "wss://")
UA = {"User-Agent": "between-visit-check/1.0"}
STATE = Path("/app/tests/.live_sim.json")
DEMO = "276dc5bb-53b0-4734-83d7-c7743052d09d"
STEP_S = float(os.environ.get("STEP_S", "1.5"))


def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(**kw):
    STATE.write_text(json.dumps({**state(), **kw}))


async def db_():
    from db import db
    return db


async def client_id():
    db = await db_()
    return (await db.clients.find_one({"display_name": "Client A (synthetic)"}, {"_id": 0, "id": 1}))["id"]


async def temp_route():
    from models import CheckpointSnapshot, Route, RouteVersion
    db = await db_()
    st = state()
    if st.get("route_id"):
        return st["route_id"]
    practice = await db.practices.find_one({}, {"_id": 0, "id": 1})
    route = Route(practice_id=practice["id"], name="TEMP P20 photo route (synthetic)", current_version=1)
    cps = [CheckpointSnapshot(id=f"cp{i}", order=i, name=n, photo_url="/api/photos/none", landmark_text=t) for i, (n, t) in
           enumerate([("Start", "Start of the corridor"), ("Corner", "The corridor turns right"), ("End", "End wall")], 1)]
    await db.routes.insert_one(route.to_mongo())
    await db.route_versions.insert_one(RouteVersion(route_id=route.id, version=1, checkpoints=cps, author="check").to_mongo())
    save(route_id=route.id)
    return route.id


def new_attempt(route_id, cid):
    r = requests.post(f"{API}/routes/{route_id}/exercises", json={"client_id": cid, "goal": "Phase 20 live check", "stop_rule": "Stop if unsure"}, headers=UA).json()
    a = {"id": r["attempt"]["id"], "stream_id": r["attempt"]["stream_id"], "key": r["key"], "exercise_id": r["exercise"]["id"]}
    save(attempts=state().get("attempts", []) + [a], current=a)
    return a


def phone_line(M, h, ts):
    return json.dumps({"type": "phone", "ar_tracking": "normal", "ar_pose": M.flatten(order="F").tolist(), "heading_deg": h, "has_lidar": True, "ts_capture_ms": ts})


def live():
    return requests.get(f"{API}/attempts/{state()['current']['id']}/live", headers=UA).json()


async def steps_demo():
    db = await db_()
    from storage import get_object
    rec = await db.recordings.find_one({"route_id": DEMO, "kind": "synthetic"}, {"_id": 0})
    out = []
    for f in rec["frames"]:
        p, h = f["pose"], f["pose"]["heading_deg"]
        out.append((np.array([p["x"], 1.4, p["z"]]), h, await get_object(f["path"]), None))
    return out


def steps_corridor(depth):
    pts = [((0, 0, -0.3 * i), 0.0) for i in range(34)] + [((0.3 * i, 0, -10), 90.0) for i in range(1, 21)]
    return [(np.array(p, float), h, None, depth) for p, h in pts]


async def run(mode):
    cid = await client_id()
    route_id = DEMO if mode == "demo" else await temp_route()
    a = new_attempt(route_id, cid)
    K = {**UA, "X-Stream-Key": a["key"]}
    steps = await steps_demo() if mode == "demo" else steps_corridor(mode == "depth")
    lat, sizes = [], []
    async with websockets.connect(f"{WSS}/ws/ingest/{a['stream_id']}?key={a['key']}", max_size=None, ping_interval=None) as ws:
        await ws.recv()
        print("start:", requests.post(f"{API}/run/{a['id']}/start", headers=K).json()["status"])
        t0 = time.time()
        for i, (pos, h, jpeg, depth) in enumerate(steps):
            fwd = (math.sin(math.radians(h)), 0, -math.cos(math.radians(h)))
            M = pose(pos, fwd)
            ts = 1000 + i * 100
            before = len(live()["three"]["run_trail"])
            sent = time.time()
            await ws.send(phone_line(M, h, ts))
            if depth:
                await ws.send(depth_frame(M, ts + 10))
            if jpeg:
                await ws.send(jpeg)
            if i > 0 and i % 4 == 0:
                for _ in range(30):
                    if len(live()["three"]["run_trail"]) > before:
                        lat.append(time.time() - sent)
                        break
                    await asyncio.sleep(0.05)
            if mode != "demo" and i % 10 == 9:
                sizes.append(len(requests.get(f"{API}/attempts/{a['id']}/live/points", headers=UA).content))
            await asyncio.sleep(max(0, t0 + (i + 1) * STEP_S - time.time()))
        await asyncio.sleep(3)
        s = live()
        fr = requests.get(f"{API}/attempts/{a['id']}/live-frame", headers=UA)
        pts = requests.get(f"{API}/attempts/{a['id']}/live/points", headers=UA)
        print(f"before end: status {s['status']} live {s['live']} trail {len(s['three']['run_trail'])} dots {len(s['three']['dots'])} entities {len(s['three']['entities'])} "
              f"points {s['three']['scene']['points']} grid {s['three']['scene'].get('grid')} | caption {s['caption']} | last cp {s['last_checkpoint']} | spoken {s['cues_spoken']} held {s['cues_held_back']}")
        print(f"live-frame: {fr.status_code} {fr.headers.get('content-type')} {len(fr.content)} B, cache {fr.headers.get('cache-control')} | points fetch {len(pts.content)} B ({len(pts.content) // 12} pts), cache {pts.headers.get('cache-control')}")
        if lat:
            print(f"pose -> /live trail latency: median {np.median(lat) * 1000:.0f} ms, max {max(lat) * 1000:.0f} ms (n={len(lat)})")
        if sizes:
            print("points fetch sizes while walking (B):", sizes)
        if os.environ.get("NO_END"):
            return
        print("end:", requests.post(f"{API}/run/{a['id']}/end", headers=K).json()["status"])
    s = live()
    fr = requests.get(f"{API}/attempts/{a['id']}/live-frame", headers=UA)
    pts = requests.get(f"{API}/attempts/{a['id']}/live/points", headers=UA)
    print(f"after end: status {s['status']} live {s['live']} frame_url {s['frame_url']} review {s['review_path']} | live-frame {fr.status_code} {len(fr.content)} B | points {len(pts.content)} B")


async def cleanup():
    db = await db_()
    from migrations import delete_routes_cascade
    st = state()
    ids = [a["id"] for a in st.get("attempts", [])]
    ex = [a["exercise_id"] for a in st.get("attempts", [])]
    if st.get("route_id"):
        print(await delete_routes_cascade([st["route_id"]]))
    print("events", (await db.attempt_events.delete_many({"attempt_id": {"$in": ids}})).deleted_count, "attempts", (await db.attempts.delete_many({"id": {"$in": ids}})).deleted_count,
          "exercises", (await db.exercises.delete_many({"id": {"$in": ex}})).deleted_count)
    STATE.unlink(missing_ok=True)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    asyncio.run(cleanup() if sys.argv[1] == "cleanup" else run(sys.argv[1]))
