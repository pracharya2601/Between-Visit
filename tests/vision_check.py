import asyncio, io, json, sys, time
import requests, websockets
from PIL import Image

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")
from db import db  # noqa: E402
import vision_worker  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
UA = {"User-Agent": "between-visit-check/1.0"}
d = json.load(open("/app/tests/.run_check.json"))
A = d["attempts"][0]
K = {**UA, "X-Stream-Key": A["key"]}
RUN = f"{API}/run/{A['id']}"
CORRIDOR = requests.get(sys.argv[1], timeout=30).content
buf = io.BytesIO(); Image.new("RGB", (640, 480), (0, 0, 0)).save(buf, "JPEG"); BLACK = buf.getvalue()


def events(types=("vision", "vision_error", "vision_stopped")):
    return [e for e in requests.get(f"{API}/attempts/{A['id']}/events", headers=UA).json() if e["type"] in types]


def frame(data):
    return requests.post(f"{API}/attempts/{A['id']}/frame", data=data, headers={**K, "Content-Type": "image/jpeg"}).status_code


async def stream(seconds, fps=5):
    url = f"{API.replace('https://', 'wss://')}/ws/ingest/{A['stream_id']}?key={A['key']}"
    sent = 0
    async with websockets.connect(url) as ws:
        await ws.recv()
        end = time.time() + seconds
        while time.time() < end:
            await ws.send(CORRIDOR); sent += 1
            await asyncio.sleep(1 / fps)
    return sent


async def wait_new(n_before, timeout=12):
    t = time.time()
    while time.time() - t < timeout:
        ev = events()
        if len(ev) > n_before:
            return ev
        await asyncio.sleep(0.5)
    return events()


async def main():
    print("start:", requests.post(f"{RUN}/start", headers=K).json()["status"])
    s0 = requests.get(f"{API}/attempts/{A['id']}/status", headers=UA).json()
    t0 = time.time()
    sent = await stream(20)
    t_stop = time.time()
    at_stop = len(events())
    await asyncio.sleep(10)
    ev = sorted(events(), key=lambda e: e["seq"])
    s1 = requests.get(f"{API}/attempts/{A['id']}/status", headers=UA).json()
    after = [e for e in ev if e["seq"] / 1e9 > t_stop + 0.2]
    lat = [e["latency_ms"] for e in ev if e["type"] == "vision"]
    print(f"RATE: sent {sent} frames in 20s, glasses frames counted +{s1['glasses_frames'] - s0['glasses_frames']}, vision calls {len(ev)} ({len(ev) / (t_stop - t0):.2f}/s), events finishing after the stream stopped: {len(after)} (in-flight at stop: {len(ev) - at_stop})")
    print("  types:", {t: sum(e['type'] == t for e in ev) for t in ('vision', 'vision_error')}, "| latency ms min/avg/max:", min(lat), sum(lat) // len(lat), max(lat))
    starts = [e["seq"] / 1e9 - e["latency_ms"] / 1000 for e in ev]
    print("  min gap between call starts (s):", round(min(b - a for a, b in zip(starts, starts[1:])), 2))
    print("  sample result:", ev[-1]["result"], "| model:", ev[-1]["model"], "| route_version:", ev[-1]["route_version"], "| source:", ev[-1]["source"], "| spoken:", ev[-1]["spoken"])

    print("pause:", requests.post(f"{RUN}/pause", headers=K).json()["status"])
    n = len(events()); await stream(5); await asyncio.sleep(3)
    print("PAUSED: new vision events while paused:", len(events()) - n)
    print("resume:", requests.post(f"{RUN}/resume", headers=K).json()["status"])

    n = len(events()); print("black frame POST:", frame(BLACK))
    ev = await wait_new(n)
    print("BLACK:", ev[0]["type"], "unusable =", (ev[0].get("result") or {}).get("unusable"), "| source:", ev[0]["source"], "| latency:", ev[0]["latency_ms"])

    n = len(events())
    await vision_worker.analyse(A["id"], CORRIDOR, "phone", timeout=0.01)
    ev = events()
    print("FORCED TIMEOUT:", ev[0]["type"], ev[0]["reason"], ev[0]["latency_ms"], "ms", ev[0]["model"])
    await asyncio.sleep(1.2); n = len(events()); frame(CORRIDOR)
    ev = await wait_new(n)
    print("NEXT FRAME AFTER ERROR:", ev[0]["type"], ev[0].get("result"))

    await db.attempts.update_one({"id": A["id"]}, {"$set": {"active_seconds": 30 * 60 + 1}})
    await asyncio.sleep(1.2); n = len(events()); frame(CORRIDOR)
    ev = await wait_new(n)
    print("CAP:", ev[0]["type"], ev[0].get("reason"))
    for _ in range(3):
        await asyncio.sleep(1.3); frame(CORRIDOR)
    await asyncio.sleep(4)
    ev = events()
    print("  after 3 more frames: new events", len(ev) - n, "| vision_stopped count:", sum(e["type"] == "vision_stopped" for e in ev))

    allev = requests.get(f"{API}/attempts/{A['id']}/events", headers=UA)
    body = allev.text
    seqs = [e["seq"] for e in allev.json()]
    print("EVENTS API:", allev.status_code, len(seqs), "events, newest first:", seqs == sorted(seqs, reverse=True), "| contains key/hash:", A["key"] in body or "key_hash" in body, "| contains base64 jpeg:", "/9j/" in body, "| unknown id:", requests.get(f"{API}/attempts/nope/events", headers=UA).status_code)
    print("end:", requests.post(f"{RUN}/end", headers=K).json()["status"])

asyncio.run(main())
