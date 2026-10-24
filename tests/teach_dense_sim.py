"""Dense teach walk to exceed the 50,000-point browser limit. No JPEGs and no Save, so nothing goes to storage.
Usage: python3 teach_dense_sim.py walk | cancel"""
import asyncio, json, sys, time
from pathlib import Path
import numpy as np
import requests, websockets

src = Path("/app/tests/teach_walk_sim.py").read_text().split("def get(p)")[0]
ns = {}
exec(src.replace("EMPTY = requests", "EMPTY = None #").replace("PERSON = requests", "PERSON = None #"), ns)
API, WSS, UA, pose, depth_frame, path = ns["API"], ns["WSS"], ns["UA"], ns["pose"], ns["depth_frame"], ns["path"]
STATE = Path("/app/tests/.teach_dense.json")


async def walk():
    s = requests.post(f"{API}/teach", json={"route_name": "Teach dense sim (synthetic)"}, headers=UA).json()
    STATE.write_text(json.dumps(s))
    async with websockets.connect(f"{WSS}/ws/ingest/{s['stream_id']}?key={s['key']}", max_size=None) as ws:
        await ws.recv()
        i = 0
        for dy in (0.0, 0.5, -0.5, 1.0):
            for pos, fwd in path():
                M = pose(pos + np.array([0, dy, 0]), fwd)
                ts = 1000 + i * 100
                await ws.send(json.dumps({"type": "phone", "ar_tracking": "normal", "ar_pose": M.flatten(order="F").tolist(), "ts_capture_ms": ts}))
                await ws.send(depth_frame(M, ts + 10))
                i += 1
                await asyncio.sleep(0.03)
        await asyncio.sleep(1.5)
        print("live status:", requests.get(f"{API}/teach/{s['id']}/status", headers=UA).json())
    requests.post(f"{API}/teach/{s['id']}/finish", headers=UA)
    scene = requests.get(f"{API}/teach/{s['id']}/scene", headers=UA).json()
    r = requests.get(f"{API}/teach/{s['id']}/points", headers=UA)
    print(f"kept points: {scene['points']} | scene points_sent: {scene['points_sent']} | points endpoint: {len(r.content) // 12} points, X-Point-Count {r.headers.get('X-Point-Count')}, {len(r.content)} bytes")
    print("review:", f"/teach/{s['id']}/review")


async def cancel():
    s = json.loads(STATE.read_text())
    print("cancel:", requests.post(f"{API}/teach/{s['id']}/cancel", headers=UA).json()["status"])
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv; load_dotenv("/app/backend/.env")
    from db import db
    print("route exists:", await db.routes.count_documents({"id": s["route_id"]}), "| checkpoints:", await db.checkpoints.count_documents({"route_id": s["route_id"]}),
          "| photos for route:", await db.photos.count_documents({"route_id": s["route_id"]}),
          "| session docs deleted:", (await db.teach_sessions.delete_many({"id": s["id"]})).deleted_count)
    STATE.unlink()


asyncio.run({"walk": walk, "cancel": cancel}[sys.argv[1]]())
