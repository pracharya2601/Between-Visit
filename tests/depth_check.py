"""Phase 7 depth/pose check. Needs a temp attempt: run `python3 run_check_data.py setup` first, `cleanup` after.
Usage: python3 depth_check.py <jpeg-url>"""
import asyncio, json, struct, sys, time
import numpy as np
import requests, websockets

sys.path.insert(0, "/app/backend")
import sensors  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
UA = {"User-Agent": "between-visit-check/1.0"}
d = json.load(open("/app/tests/.run_check.json"))
A = d["attempts"][0]
K = {**UA, "X-Stream-Key": A["key"]}
RUN = f"{API}/run/{A['id']}"
JPEG = requests.get(sys.argv[1], timeout=30).content
W, H = 256, 192


def dpt1(ts, values=(1000, 2500, 5000), fmt=1, w=W, h=H, extra=b""):
    arr = np.full((h, w), 300, dtype="<u2")
    if w and h:
        mid = slice(h // 3, h - h // 3)
        c1, c2 = w // 3, w - w // 3
        for cols, v in zip((slice(0, c1), slice(c1, c2), slice(c2, w)), values):
            arr[mid, cols] = v
    header = struct.pack("<4sHHdffffB3x", b"DPT1", w, h, float(ts), 200.0, 200.0, w / 2, h / 2, fmt)
    return header + arr.tobytes() + extra


def phone(ts, x=1.25, z=-3.5, heading=87.5, tracking="normal", pose=None, **extra):
    m = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, x, 0.0, z, 1.0]
    return json.dumps({"type": "phone", "ar_tracking": tracking, "ar_pose": pose if pose is not None else m, "heading_deg": heading, "has_lidar": True, "ts_capture_ms": ts, **extra})


def status():
    return requests.get(f"{API}/attempts/{A['id']}/status", headers=UA).json()


def vision_events():
    return [e for e in requests.get(f"{API}/attempts/{A['id']}/events", headers=UA).json() if e["type"].startswith("vision")]


async def wait_vision(n, timeout=12):
    t = time.time()
    while time.time() - t < timeout:
        ev = vision_events()
        if len(ev) > n:
            return ev[0]
        await asyncio.sleep(0.4)


def lcr(s):
    return (s["depth_left"], s["depth_centre"], s["depth_right"])


async def main():
    print("start:", requests.post(f"{RUN}/start", headers=K).json()["status"])
    url = f"{API.replace('https://', 'wss://')}/ws/ingest/{A['stream_id']}?key={A['key']}"
    async with websockets.connect(url, max_size=None) as ws:
        await ws.recv()
        s0 = status()
        await ws.send(phone(1000, ar_planes=[{"a": 1}], ar_points=[[0, 0, 0]], unknown_field="x"))
        await ws.send(dpt1(1030)); await asyncio.sleep(0.6)
        s = status()
        print(f"JRN-90 valid: depth frames +{s['depth_frames_received'] - s0['depth_frames_received']}, frames_received +{s['frames_received'] - s0['frames_received']}, L/C/R {lcr(s)}, pose x,z {s['pose_x']}, {s['pose_z']}, heading {s['heading_deg']}, tracking {s['ar_tracking']}")
        b = status()
        await ws.send(dpt1(1030)[:-2]); await asyncio.sleep(0.4)
        await ws.send(dpt1(1030, fmt=2)); await ws.send(dpt1(1030, w=0)); await ws.send(b"DPT1" + b"\x00" * 10)
        await ws.send(dpt1(1030, w=1024, h=600)); await asyncio.sleep(0.5)
        s = status()
        print(f"JRN-91/92 bad frames (wrong length, format 2, width 0, short, >1 MB): depth_dropped +{s['depth_dropped'] - b['depth_dropped']}, frames_dropped +{s['frames_dropped'] - b['frames_dropped']}, connection open: {ws.state.name}")
        await ws.send(dpt1(1200, values=(900, 900, 900))); await asyncio.sleep(0.4)
        s2 = status()
        print(f"JRN-93 unpaired (ts 200 ms off): depth_unpaired +{s2['depth_unpaired'] - s['depth_unpaired']}, summary unchanged: {lcr(s2) == lcr(s)}")
        await ws.send(phone(2000)); await ws.send(dpt1(2010, values=(1200, 3300, 0))); await asyncio.sleep(0.4)
        print("JRN-94 right third all zero: L/C/R", lcr(status()))
        await ws.send(phone(2100, pose=[0.1] * 10, heading="north", tracking=5)); await asyncio.sleep(0.4)
        s = status()
        print(f"JRN-96 bad ar_pose (10 floats), bad heading/tracking types: pose kept {s['pose_x']}, {s['pose_z']}, heading kept {s['heading_deg']}, tracking kept {s['ar_tracking']}")

        n = len(vision_events()); b = status()
        for i in range(50):
            ts = 3000 + i * 100
            await ws.send(phone(ts)); await ws.send(dpt1(ts + 10))
            await asyncio.sleep(0.05)
        await asyncio.sleep(3)
        s = status()
        print(f"JRN-95 50 depth frames while running: depth frames +{s['depth_frames_received'] - b['depth_frames_received']}, picture frames +{s['frames_received'] - b['frames_received']}, vision events +{len(vision_events()) - n}")

        await asyncio.sleep(1.2)
        n = len(vision_events())
        await ws.send(phone(9000, x=2.5, z=-7.75, heading=181.0)); await ws.send(dpt1(9020, values=(800, 2000, 6100))); await ws.send(JPEG)
        ev = await wait_vision(n)
        print("JRN-97 fresh:", {k: ev[k] for k in ("type", "pos_x", "pos_z", "heading_deg", "ar_tracking", "depth_left", "depth_centre", "depth_right")})
        print("   prompt depth text:", ev["depth_prompt"], "| distances in result:", [(e["label"], e["distance_band"]) for e in ev["result"]["new_entities"]])
        await asyncio.sleep(1.6)
        n = len(vision_events()); await ws.send(JPEG)
        ev = await wait_vision(n)
        print("JRN-98 stale (>1 s):", {k: ev[k] for k in ("pos_x", "pos_z", "heading_deg", "ar_tracking", "depth_left", "depth_centre", "depth_right")}, "| prompt:", ev["depth_prompt"])

    pub = requests.get(RUN, headers=K).text + requests.get(f"{RUN}/cues", headers=K).text
    print("JRN-99 run page API mentions pose/depth:", any(w in pub for w in ("pos_x", "depth", "ar_pose", "heading_deg", "ar_tracking")))
    print("end:", requests.post(f"{RUN}/end", headers=K).json()["status"])

    frame = dpt1(1030)
    t = time.perf_counter()
    for _ in range(100):
        sensors.summarise(frame)
    print(f"Q-34 throughput: {(time.perf_counter() - t) * 10:.2f} ms per 256x192 frame; exact summary: {sensors.summarise(frame)[1]}")

asyncio.run(main())
