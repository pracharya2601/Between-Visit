import asyncio, json, os, time, urllib.request
import websockets

opener = urllib.request.build_opener()
opener.addheaders = [("User-Agent", "between-visit-check/1.0")]
urllib.request.install_opener(opener)

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
WSS = API.replace("https://", "wss://")
cfg = json.load(urllib.request.urlopen(f"{API}/device-test/config"))
KEY, AID = cfg["key"], cfg["attempt_id"]
URL = f"{WSS}/ws/ingest/att-test?key={KEY}"
JPEG = b"\xff\xd8\xff\xe0" + os.urandom(2000) + b"\xff\xd9"


def status():
    return json.load(urllib.request.urlopen(f"{API}/attempts/{AID}/status"))


def cue(text, priority=1):
    req = urllib.request.Request(f"{API}/attempts/{AID}/cue", data=json.dumps({"text": text, "priority": priority}).encode(), headers={"Content-Type": "application/json", "User-Agent": "between-visit-check/1.0"})
    try:
        return urllib.request.urlopen(req).status, None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


async def close_code(url):
    try:
        async with websockets.connect(url) as ws:
            await asyncio.wait_for(ws.recv(), 5)
            await asyncio.wait_for(ws.recv(), 5)
    except websockets.ConnectionClosed as e:
        return e.rcvd.code if e.rcvd else None
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


async def main():
    print("WSS base:", WSS)
    for i in range(3):
        async with websockets.connect(URL, max_size=None) as ws:
            print(f"connect {i+1}/3 first msg:", await asyncio.wait_for(ws.recv(), 5))
    print("wrong key close:", await close_code(f"{WSS}/ws/ingest/att-test?key=wrong"))
    print("no key close:", await close_code(f"{WSS}/ws/ingest/att-test"))
    print("unknown stream close:", await close_code(f"{WSS}/ws/ingest/nope?key={KEY}"))

    s0 = status()
    async with websockets.connect(URL, max_size=None) as ws:
        await ws.recv()
        await asyncio.sleep(0.5)
        print("live while connected:", status()["live"])
        for _ in range(5):
            await ws.send(JPEG)
        await asyncio.sleep(0.5)
        s1 = status()
        print("frames +", s1["frames_received"] - s0["frames_received"], "since:", s1["seconds_since_last_frame"])
        await ws.send("not json")
        await ws.send(json.dumps({"type": "motion", "ts_ns": 1, "q": [1, 0, 0, 0], "acc": [0, 0, 9.8], "gyro": [0, 0, 0], "mag": [1, 1, 1], "src": "glasses"}))
        await ws.send(json.dumps({"type": "motion", "ts_ns": 2, "q": [1, 0, 0, 0], "acc": [0, 0, 9.8], "gyro": [0, 0, 0], "mag": [2, 2, 2], "src": "glasses"}))
        await ws.send(JPEG)
        await asyncio.sleep(0.5)
        print("last motion:", status()["last_motion"])
        await ws.send(os.urandom(1_500_000))
        await ws.send(JPEG)
        await asyncio.sleep(1)
        s2 = status()
        print("after 1.5MB: dropped +", s2["frames_dropped"] - s1["frames_dropped"], "received +", s2["frames_received"] - s1["frames_received"], "(expect +1 / +2 incl motion frame)")
        t = time.time()
        print("cue POST:", cue("Turn left at the bench", 2))
        print("device got:", await asyncio.wait_for(ws.recv(), 5), f"in {time.time()-t:.2f}s")
        print("cue empty:", cue(""))
        print("cue 200 chars:", cue("x" * 200))
    await asyncio.sleep(0.5)
    print("after disconnect live:", status()["live"], "cue:", cue("hello"))
    s3 = status()
    a = await websockets.connect(URL)
    await a.recv()
    print("reconnect live:", status()["live"], "counters kept:", status()["frames_received"] == s3["frames_received"])
    b = await websockets.connect(URL)
    await b.recv()
    try:
        await asyncio.wait_for(a.recv(), 5)
    except websockets.ConnectionClosed as e:
        print("device A closed on takeover, code:", e.rcvd.code if e.rcvd else None)
    print("cue to B:", cue("For B"), await asyncio.wait_for(b.recv(), 5))
    print("live after takeover:", status()["live"])
    await b.close()


asyncio.run(main())
