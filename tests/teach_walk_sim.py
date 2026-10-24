"""Simulated teach walk (L-shaped corridor) over the public wss.
Usage: python3 teach_walk_sim.py walk | save | cleanup   (state in /app/tests/.teach_sim.json)"""
import asyncio, json, math, struct, sys, time
from pathlib import Path
import numpy as np
import requests, websockets

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
WSS = API.replace("https://", "wss://")
UA = {"User-Agent": "between-visit-check/1.0"}
STATE = Path("/app/tests/.teach_sim.json")
IMG = "https://static.prod-images.emergentagent.com/jobs/b64ebf54-447e-4e98-bd8c-1cc6c532d0bc/images/"
EMPTY = requests.get(IMG + "b86f4f5409828025d4be324127f88d16e823fcc0b3cf9269bbb184b619bcbfb7.jpeg", timeout=30).content
PERSON = requests.get(IMG + "d4e1a6ff8a2d15b11c8287d36f019e70898138ba81e5639c9794e83418db9ce4.jpeg", timeout=30).content
W, H, F, CX, CY = 256, 192, 200.0, 128.0, 96.0
# Known geometry: (axis, value, bounds on the other two axes as {axis: (lo, hi)})
PLANES = [(0, -1.0, {2: (-11, 0), 1: (-1.5, 1.5)}), (0, 1.0, {2: (-9, 0), 1: (-1.5, 1.5)}),
          (2, -11.0, {0: (-1, 7), 1: (-1.5, 1.5)}), (2, -9.0, {0: (1, 7), 1: (-1.5, 1.5)}),
          (0, 7.0, {2: (-11, -9), 1: (-1.5, 1.5)}), (1, -1.5, {0: (-1, 7), 2: (-11, 0)})]
VV, UU = np.mgrid[0:H, 0:W]
DIR_CAM = np.stack([(VV + 0.5 - CY) / F, (UU + 0.5 - CX) / F, -np.ones_like(UU, dtype=float)], -1).reshape(-1, 3)


def pose(pos, fwd):
    ez = -np.asarray(fwd, float); ex = np.array([0.0, 1.0, 0.0]); ey = np.cross(ez, ex)
    return np.column_stack([np.append(ex, 0), np.append(ey, 0), np.append(ez, 0), np.append(pos, 1)])


def depth_frame(M, ts):
    R, t = M[:3, :3], M[:3, 3]
    dirs = DIR_CAM @ R.T
    best = np.full(len(dirs), np.inf)
    for axis, val, bounds in PLANES:
        with np.errstate(divide="ignore", invalid="ignore"):
            lam = (val - t[axis]) / dirs[:, axis]
        hit = t + lam[:, None] * dirs
        ok = (lam > 0.05) & np.all([(hit[:, a] >= lo - 1e-6) & (hit[:, a] <= hi + 1e-6) for a, (lo, hi) in bounds.items()], axis=0)
        best = np.where(ok & (lam < best), lam, best)
    mm = np.where(best <= 5.0, np.round(best * 1000), 0).astype("<u2")
    return struct.pack("<4sHHdffffB3x", b"DPT1", W, H, float(ts), F, F, CX, CY, 1) + mm.tobytes()


def plane(pid, cls, align, transform, polygon):
    return {"id": pid, "align": align, "class": cls, "transform": transform, "center": transform[12:15], "extent": [2, 2], "rotation_y": 0.0, "polygon": polygon, "extra": 1}


FLOOR = plane("floor", "floor", "horizontal", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, -1.5, 0, 1], [[-1, 0], [7, 0], [7, -11], [1, -11], [1, -9], [-1, -9]])
WALL = plane("wallW", "wall", "vertical", [0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, 0, -1, 0, -5.5, 1], [[-5.5, -1.5], [5.5, -1.5], [5.5, 1.5], [-5.5, 1.5]])
DOOR = plane("door1", "door", "vertical", [-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 4, -0.5, -11, 1], [[-0.5, -1], [0.5, -1], [0.5, 1], [-0.5, 1]])
BAD = {"id": "bad", "align": "sideways", "class": "wall"}


def path():
    pts = [((0, 0, -0.15 * i), (0, 0, -1)) for i in range(67)] + [((0.15 * i, 0, -10), (1, 0, 0)) for i in range(1, 41)]
    return [(np.array(p, float), f) for p, f in pts]


def get(p):
    return requests.get(f"{API}{p}", headers=UA, timeout=30)


def dist_to_walls(pts):
    errs = []
    for p in pts:
        cands = [abs(p[a] - v) for a, v, b in PLANES if all(lo - 0.1 <= p[k] <= hi + 0.1 for k, (lo, hi) in b.items())]
        errs.append(min(cands) if cands else 9.9)
    return np.array(errs)


async def walk():
    print("empty name:", requests.post(f"{API}/teach", json={"route_name": " "}, headers=UA).status_code)
    s = requests.post(f"{API}/teach", json={"route_name": "Teach sim corridor (synthetic)"}, headers=UA).json()
    print("session:", s["stream_id"], "key present:", bool(s["key"]), "| status:", get(f"/teach/{s['id']}/status").json())
    try:
        async with websockets.connect(f"{WSS}/ws/ingest/{s['stream_id']}?key=wrong") as ws:
            await ws.recv(); await ws.recv()
    except websockets.ConnectionClosed as e:
        print("wrong key ->", e.rcvd.code)
    steps = path(); corner_i = 66; n = len(steps)
    async with websockets.connect(f"{WSS}/ws/ingest/{s['stream_id']}?key={s['key']}", max_size=None) as ws:
        print("connect:", await ws.recv(), "| live:", get(f"/teach/{s['id']}/status").json()["live"])
        t0 = time.time(); frame_ms = []
        for i, (pos, fwd) in enumerate(steps):
            ts = 1000 + i * 100
            M = pose(pos, fwd)
            tracking = "limited" if 20 <= i < 30 else "normal"
            line = {"type": "phone", "ar_tracking": tracking, "ar_pose": M.flatten(order="F").tolist(), "heading_deg": 0.0, "has_lidar": True, "ts_capture_ms": ts}
            if i == 5: line["ar_planes"] = [FLOOR, WALL, DOOR, BAD]
            if i == 40: line["ar_planes"] = [FLOOR, WALL]
            if i in (19, 30):
                pts_before = get(f"/teach/{s['id']}/status").json()["points"]
                print(f"  points at step {i}: {pts_before}")
            await ws.send(json.dumps(line))
            if i == 6:
                await asyncio.sleep(0.2); print("  planes after first set (floor, wall, door + 1 malformed):", get(f"/teach/{s['id']}/status").json()["planes"])
            await ws.send(depth_frame(M, ts + 10))
            if i % 2 == 0 or i == corner_i:
                await ws.send(PERSON if i == corner_i or i >= n - 9 else EMPTY)
            await asyncio.sleep(max(0, t0 + (i + 1) * 0.1 - time.time()))
        await asyncio.sleep(1.5)
        st = get(f"/teach/{s['id']}/status").json()
        print("after walk:", st)
    fin = requests.post(f"{API}/teach/{s['id']}/finish", headers=UA).json()
    print("finish:", fin["status"], "key after finish:", fin["key"])
    for _ in range(60):
        cps = get(f"/routes/{s['route_id']}").json()["checkpoints"]
        if cps and not any(c["photo_pending"] for c in cps):
            break
        time.sleep(2)
    for c in cps:
        print(f"  {c['order']}. {c['name']} at {[round(v, 2) for v in c['position']]} photo={bool(c['photo_url'])} needs_photo={c['needs_photo']} text={c['landmark_text'][:60]!r}")
    scene = get(f"/teach/{s['id']}/scene").json()
    pts = np.frombuffer(get(f"/teach/{s['id']}/points").content, dtype="<f4").reshape(-1, 3)
    err = dist_to_walls(pts)
    print(f"scene: {scene['points']} points kept, {len(pts)} sent to browser, planes {[p['class'] for p in scene['planes']]}, trail {len(scene['trail'])} pts, {scene['metres_walked']} m")
    print(f"wall error: max {err.max():.3f} m, 99th pct {np.percentile(err, 99):.3f} m")
    ev = get(f"/attempts/{s['id']}/events")
    print("vision events for the teach stream:", ev.status_code, "(no attempt with this id)")
    photo_ids = [c["photo_url"].split("/")[-1] for c in cps if c["photo_url"]]
    STATE.write_text(json.dumps({"session": s, "photos": photo_ids}))


def save():
    st = json.loads(STATE.read_text()); s = st["session"]; rid = s["route_id"]
    cps = get(f"/routes/{rid}").json()["checkpoints"]
    end = [c for c in cps if c["needs_photo"]]
    if end:
        r = requests.post(f"{API}/checkpoints/{end[0]['id']}/photo", files={"file": ("e.jpg", EMPTY, "image/jpeg")}, headers=UA).json()
        print("upload for 'Needs photo':", r["ai_status"], "| needs_photo now:", r["checkpoint"]["needs_photo"])
        st["photos"].append(r["checkpoint"]["photo_url"].split("/")[-1])
    print("save before approve:", requests.post(f"{API}/teach/{s['id']}/save", headers=UA).json()["detail"])
    requests.patch(f"{API}/checkpoints/{cps[0]['id']}", json={"name": "Entrance doors"}, headers=UA)
    requests.delete(f"{API}/checkpoints/{cps[-1]['id']}", headers=UA)
    for c in get(f"/routes/{rid}").json()["checkpoints"]:
        requests.post(f"{API}/checkpoints/{c['id']}/approve", headers=UA)
    r = requests.post(f"{API}/teach/{s['id']}/save", headers=UA).json()
    v = get(f"/routes/{rid}/versions").json()
    print("save:", r, "| v1 memory_id:", v[0]["memory_id"], "| names:", [c["name"] for c in v[0]["checkpoints"]])
    print("session after save:", get(f"/teach/{s['id']}").json(), "| in Routes list:", any(x["id"] == rid for x in get("/routes").json()))
    client = [c for c in get("/clients").json() if "A" in c["display_name"]][0]
    a = requests.post(f"{API}/routes/{rid}/exercises", json={"client_id": client["id"], "goal": "Teach sim run", "stop_rule": "Stop and press Help."}, headers=UA).json()
    att, key = a["attempt"], a["key"]
    K = {**UA, "X-Stream-Key": key}
    print("run start:", requests.post(f"{API}/run/{att['id']}/start", headers=K).json()["status"])

    async def run_walk():
        async with websockets.connect(f"{WSS}/ws/ingest/{att['stream_id']}?key={key}") as ws:
            await ws.recv()
            for i in range(31):
                M = pose(np.array([0, 0, -0.1 * i]), (0, 0, -1))
                await ws.send(json.dumps({"type": "phone", "ar_tracking": "normal", "ar_pose": M.flatten(order="F").tolist(), "ts_capture_ms": i * 100, "ar_planes": [FLOOR]}))
                await ws.send(depth_frame(M, i * 100 + 10))
                await asyncio.sleep(0.05)
            await asyncio.sleep(0.5)
    asyncio.run(run_walk())
    trail = get(f"/attempts/{att['id']}/trail").json()
    pub = requests.get(f"{API}/run/{att['id']}", headers=K).text + requests.get(f"{API}/run/{att['id']}/cues", headers=K).text
    leak = any(w in pub for w in ('"trail"', '"planes"', 'pos_x', 'memory_id', 'ar_planes'))
    print(f"run trail: {len(trail)} points over 3 m | run API mentions trail/planes/memory: {leak}")
    c0 = get(f"/routes/{rid}").json()["checkpoints"][0]
    requests.patch(f"{API}/checkpoints/{c0['id']}", json={"name": "Entrance doors (v2)"}, headers=UA)
    requests.post(f"{API}/checkpoints/{c0['id']}/approve", headers=UA)
    v2 = requests.post(f"{API}/routes/{rid}/save", headers=UA).json()
    print("builder save:", v2["version"], "| v2 memory_id same as v1:", v2["memory_id"] == v[0]["memory_id"])
    c = requests.post(f"{API}/teach", json={"route_name": "Teach sim cancel (synthetic)"}, headers=UA).json()

    async def cancel_walk():
        async with websockets.connect(f"{WSS}/ws/ingest/{c['stream_id']}?key={c['key']}") as ws:
            await ws.recv()
            counts = []
            for i in range(20):
                M = pose(np.array([0, 0, -0.3 * i]), (0, 0, -1))
                tracking = "normal" if i < 10 else "limited"
                await ws.send(json.dumps({"type": "phone", "ar_tracking": tracking, "ar_pose": M.flatten(order="F").tolist(), "ts_capture_ms": i * 100}))
                await ws.send(depth_frame(M, i * 100 + 10))
                if i in (9, 19):
                    await asyncio.sleep(0.8); counts.append(get(f"/teach/{c['id']}/status").json()["points"])
            print(f"limited tracking: points after 10 normal frames {counts[0]}, after 10 more limited frames {counts[1]}")
            await asyncio.sleep(0.5)
            r = requests.post(f"{API}/teach/{c['id']}/cancel", headers=UA).json()
            try:
                await asyncio.wait_for(ws.recv(), 3)
            except websockets.ConnectionClosed as e:
                print("cancel:", r["status"], "key:", r["key"], "| socket closed:", e.rcvd.code, "| route gone:", get(f"/routes/{c['route_id']}").status_code, "| points:", get(f"/teach/{c['id']}/points").status_code)
    asyncio.run(cancel_walk())
    st.update(cancel_id=c["id"]); STATE.write_text(json.dumps(st))


async def cleanup():
    sys.path.insert(0, "/app/backend")
    from dotenv import load_dotenv; load_dotenv("/app/backend/.env")
    from db import db
    from migrations import delete_routes_cascade
    st = json.loads(STATE.read_text()); s = st["session"]
    mem = await db.route_memories.find({"route_id": s["route_id"]}, {"_id": 0}).to_list(10)
    print(await delete_routes_cascade([s["route_id"]]))
    print("route_memories deleted:", (await db.route_memories.delete_many({"route_id": s["route_id"]})).deleted_count, "| leftover memory blobs:", [m[k] for m in mem for k in ("points_path", "json_path")])
    print("teach sessions deleted:", (await db.teach_sessions.delete_many({"id": {"$in": [s["id"], st.get("cancel_id")]}})).deleted_count)
    print("photos now unservable:", st["photos"], [get(f"/photos/{p}").status_code for p in st["photos"]])
    STATE.unlink()


{"walk": lambda: asyncio.run(walk()), "save": save, "cleanup": lambda: asyncio.run(cleanup())}[sys.argv[1]]()
