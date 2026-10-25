"""Phase 11 memory checks (needs CUE_TEST_HOOK=1 while running; turn it off afterwards).
  python3 memory_check.py rerun3d     New attempt on the 3D demo exercise, same simulated run; prints chair reasons; deletes that attempt
  python3 memory_check.py temp        temporary copies of both demo routes: runs, Edit/Dismiss/409/Confirm (with depth), 2D segment confirm + rerun
  python3 memory_check.py remove      Remove the edited bench on the temp 3D copy; history + version-integrity compare
  python3 memory_check.py cleanup     delete the temporary routes, attempts, events and corrections
"""
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
import requests
import websockets

import review_demo as rd
import teach_walk_sim as tw
from db import db
from migrations import delete_routes_cascade
from models import Route, RouteVersion

API, WSS, UA = rd.API, rd.WSS, rd.UA
STATE = Path("/app/tests/.memory_check.json")
DEMO = json.loads(Path("/app/tests/.review_demo.json").read_text())


def get(p):
    return requests.get(f"{API}{p}", headers=UA, timeout=60).json()


def mover_3d(att, key, origin, depth):
    async def mover(state):
        d, i = 0.0, 0
        async with websockets.connect(f"{WSS}/ws/ingest/{att['stream_id']}?key={key}", additional_headers=UA) as ws:
            await ws.recv()
            while not state["stop"]:
                if not state["paused"]:
                    d += 0.1
                x, z = rd.walk_xz(d)
                M = tw.pose(np.array([origin[0] + x, 0.0, origin[1] + z]), (0, 0, -1) if d <= 10 else (1, 0, 0))
                await ws.send(json.dumps({"type": "phone", "ar_tracking": "normal", "ar_pose": M.flatten(order="F").tolist(), "heading_deg": 0.0 if d <= 10 else 90.0, "has_lidar": depth, "ts_capture_ms": i * 200}))
                if depth:
                    await ws.send(tw.depth_frame(M, i * 200 + 10))
                if i % 2 == 0:
                    await ws.send(tw.EMPTY)
                i += 1
                await asyncio.sleep(0.2)
    return mover


def mover_2d(att, key):
    async def mover(state):
        walked, steps = 0.0, 0
        while not state["stop"]:
            if not state["paused"]:
                walked += 1.0
                steps = int(walked * 1.4)
            await asyncio.to_thread(requests.post, f"{API}/attempts/{att['id']}/frame", params={"heading": 2.0 if walked <= 12 else 91.0, "steps": steps}, data=tw.EMPTY,
                                    headers={**UA, "X-Stream-Key": key, "Content-Type": "image/jpeg"}, timeout=30)
            await asyncio.sleep(0.8)
    return mover


async def simulate(made, cps, mover):
    await rd.run_script(made["attempt"], made["key"], cps, rd.script_for(cps), mover)


def entity_items(aid):
    return [i for i in get(f"/attempts/{aid}/review")["timeline"] if i["entity"]]


def show(aid, title):
    print(title)
    for i in entity_items(aid):
        print(f"   {i['at']:>5}s {i['category']:<10} {i['text']:<40} reason={i['reason']} correction={(i['correction'] or {}).get('action')}")


async def drop_attempt(aid):
    ev = await db.attempt_events.distinct("id", {"attempt_id": aid})
    r = (await db.corrections.delete_many({"attempt_event_id": {"$in": ev}})).deleted_count, (await db.attempt_events.delete_many({"attempt_id": aid})).deleted_count, (await db.attempts.delete_many({"id": aid})).deleted_count
    print("   deleted corrections/events/attempts:", r)


async def rerun3d():
    d = DEMO["3d"]
    made = rd.post(f"/exercises/{d['exercise_id']}/attempts")
    print("new attempt version:", made["attempt"]["route_version"], "| demo attempt version:", (await db.attempts.find_one({"id": d["attempt_id"]}))["route_version"])
    cps = get(f"/routes/{d['route_id']}/versions")[-1]["checkpoints"]
    await simulate(made, cps, mover_3d(made["attempt"], made["key"], (2.0, -1.0), False))
    show(made["attempt"]["id"], "NEW 3D ATTEMPT object items:")
    await drop_attempt(made["attempt"]["id"])


async def copy_route(src_id, name):
    src = await db.routes.find_one({"id": src_id}, {"_id": 0})
    v1 = await db.route_versions.find_one({"route_id": src_id, "version": 1}, {"_id": 0})
    route = Route(practice_id=src["practice_id"], name=name, current_version=1)
    await db.routes.insert_one(route.to_mongo())
    await db.route_versions.insert_one(RouteVersion(route_id=route.id, version=1, checkpoints=v1["checkpoints"], memory_id=v1.get("memory_id"), author=v1["author"], note="route saved").to_mongo())
    return route.id, v1["checkpoints"]


async def temp():
    snap = {f"{v['route_id']}:{v['version']}": v for v in await db.route_versions.find({}, {"_id": 0}).to_list(1000)}
    st = {"snapshot": snap}
    r3, cps3 = await copy_route(DEMO["3d"]["route_id"], "Memory check copy 3D (synthetic)")
    m3 = rd.assign(r3, "standard")
    await simulate(m3, cps3, mover_3d(m3["attempt"], m3["key"], (0.0, 0.0), True))
    a3 = m3["attempt"]["id"]
    items = entity_items(a3)
    show(a3, "TEMP 3D (with depth) object items:")
    spoken = [i for i in items if i["category"] == "spoken"]
    cart = next(i for i in spoken if i["entity"]["label"] == "cart")
    chair = next(i for i in spoken if i["entity"]["label"] == "chair")
    low = next(i for i in items if i["entity"]["label"] == "sign stand")
    corr = lambda i, b: requests.post(f"{API}/attempt-events/{i['id']}/correction", json=b, headers=UA)
    e = corr(chair, {"action": "edit", "label": "bench", "side": "left"}); print("JRN-157 edit chair -> bench/left:", e.status_code, e.json())
    x = corr(low, {"action": "dismiss"}); print("JRN-158 dismiss sign stand:", x.status_code, x.json())
    print("JRN-159 second correction on the dismissed item:", corr(low, {"action": "confirm"}).status_code, "| on the edited item:", corr(chair, {"action": "dismiss"}).status_code)
    print("   bad label (41 chars):", corr(cart, {"action": "edit", "label": "x" * 41}).status_code)
    c = corr(cart, {"action": "confirm"}); print("confirm cart (depth):", c.status_code, c.json()["new_route_version"])
    vs = get(f"/routes/{r3}/versions")
    print("temp 3D versions:", [(v["version"], v["note"], [(k["label"], k["side"], k["segment"], k["position"]) for k in v["known_entities"]]) for v in vs])
    print("markers in temp 3D review:", [(m["label"], m["pos"]) for m in get(f"/attempts/{a3}/review")["path"]["entities"]])
    r2, cps2 = await copy_route(DEMO["2d"]["route_id"], "Memory check copy 2D (synthetic)")
    m2 = rd.assign(r2, "minimal")
    await simulate(m2, cps2, mover_2d(m2["attempt"], m2["key"]))
    a2 = m2["attempt"]["id"]
    ch2 = next(i for i in entity_items(a2) if i["entity"]["label"] == "chair" and i["category"] == "spoken")
    c2 = corr(ch2, {"action": "confirm"}); print("JRN-161 confirm 2D chair:", c2.status_code, c2.json()["new_route_version"])
    print("   2D v2 entity:", [(k["label"], k["segment"], k["position"]) for k in get(f"/routes/{r2}/versions")[-1]["known_entities"]])
    print("   2D review markers (pos None = listed, not drawn):", [(m["label"], m["pos"]) for m in get(f"/attempts/{a2}/review")["path"]["entities"]])
    ex2 = (await db.attempts.find_one({"id": a2}))["exercise_id"]
    n2 = rd.post(f"/exercises/{ex2}/attempts")
    print("   2D new attempt version:", n2["attempt"]["route_version"])
    await simulate(n2, cps2, mover_2d(n2["attempt"], n2["key"]))
    show(n2["attempt"]["id"], "   2D NEW ATTEMPT object items (segment matching):")
    st.update({"routes": [r3, r2], "temp3d_attempt": a3})
    STATE.write_text(json.dumps(st))


async def remove():
    st = json.loads(STATE.read_text())
    r3 = st["routes"][0]
    h = get(f"/routes/{r3}/history")
    bench = next(k for k in h["known_entities"] if k["label"] == "bench")
    print("JRN-160 remove bench:", requests.post(f"{API}/routes/{r3}/known-entities/{bench['id']}/remove", headers=UA).json())
    h = get(f"/routes/{r3}/history")
    print("   history:", [f"v{v['version']}: {v['note']} by {v['author']}" for v in h["versions"]], "| current known:", [k["label"] for k in h["known_entities"]])
    now = {f"{v['route_id']}:{v['version']}": v for v in await db.route_versions.find({}, {"_id": 0}).to_list(1000)}
    changed = [k for k, v in st["snapshot"].items() if k in now and now[k] != v]
    print(f"Q-50 versions modified after creation: {len(changed)} (compared {len(st['snapshot'])} pre-existing versions) {changed}")


async def cleanup():
    st = json.loads(STATE.read_text())
    for rid in st["routes"]:
        ex = await db.exercises.distinct("id", {"route_id": rid})
        atts = await db.attempts.distinct("id", {"exercise_id": {"$in": ex}})
        evs = await db.attempt_events.distinct("id", {"attempt_id": {"$in": atts}})
        print("corrections deleted:", (await db.corrections.delete_many({"attempt_event_id": {"$in": evs}})).deleted_count, "| route:", await delete_routes_cascade([rid]))
    STATE.unlink()


if __name__ == "__main__":
    asyncio.run({"rerun3d": rerun3d, "temp": temp, "remove": remove, "cleanup": cleanup}[sys.argv[1]]())
