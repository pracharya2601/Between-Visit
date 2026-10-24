import asyncio, json, os, time
import requests, websockets

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
UA = {"User-Agent": "between-visit-check/1.0"}
d = json.load(open("/app/tests/.run_check.json"))
A = d["attempts"][0]
RUN = f"{API}/run/{A['id']}"
K = {**UA, "X-Stream-Key": A["key"]}


def st(r):
    return f"{r.status_code} {r.json().get('status', r.json().get('detail', ''))}" if r.content else str(r.status_code)


def post(path, headers=K, **kw):
    return requests.post(f"{RUN}{path}", headers=headers, timeout=30, **kw)


print("GET no key:", requests.get(RUN, headers=UA).status_code, "| wrong key:", requests.get(RUN, headers={**UA, "X-Stream-Key": "nope"}).status_code, "| key in URL only:", requests.get(f"{RUN}?key={A['key']}", headers=UA).status_code)
print("start wrong key:", post("/start", headers={**UA, "X-Stream-Key": "nope"}).status_code, "| status still:", requests.get(RUN, headers=K).json()["state"]["status"])
info = requests.get(RUN, headers=K).json()
print("info:", info["goal"][:40], "|", info["checkpoints"], "|", info["stop_rule"][:30], "|", info["stream_id"], info["state"]["status"])
print("message before start:", requests.post(f"{API}/attempts/{A['id']}/message", json={"text": "hi"}, headers=UA).status_code)
print("pause before start:", post("/pause").status_code)
print("start:", st(post("/start")), "| start again:", post("/start").status_code)
time.sleep(2)
print("pause:", st(post("/pause")))
e1 = requests.get(RUN, headers=K).json()["state"]["elapsed_seconds"]; time.sleep(2)
e2 = requests.get(RUN, headers=K).json()["state"]["elapsed_seconds"]
print(f"elapsed while paused: {e1} -> {e2} (should not change)")
print("resume:", st(post("/resume")), "| resume again:", post("/resume").status_code)
print("message empty:", requests.post(f"{API}/attempts/{A['id']}/message", json={"text": "  "}, headers=UA).status_code, "| 200 chars:", requests.post(f"{API}/attempts/{A['id']}/message", json={"text": "x" * 200}, headers=UA).status_code)
print("repeat with no cue:", post("/repeat").json())


async def glasses():
    url = f"{API.replace('https://', 'wss://')}/ws/ingest/{A['stream_id']}?key={A['key']}"
    async with websockets.connect(url) as ws:
        print("glasses connect:", await ws.recv())
        for _ in range(3):
            await ws.send(os.urandom(5000))
        await asyncio.sleep(0.5)
        s = requests.get(f"{API}/attempts/{A['id']}/status", headers=UA).json()
        print("glasses frames:", s["glasses_frames"], "| phone frames:", s["phone_frames"], "| run says glasses_live:", requests.get(RUN, headers=K).json()["state"]["glasses_live"])
        r = requests.post(f"{API}/attempts/{A['id']}/message", json={"text": "Stay where you are, I'm calling you."}, headers=UA).json()
        print("message:", r["sent_to_glasses"], "| glasses got:", await asyncio.wait_for(ws.recv(), 5))
        print("repeat (live):", post("/repeat").json()["resent_to_glasses"], "| glasses got again:", await asyncio.wait_for(ws.recv(), 5))
    await asyncio.sleep(0.5)
    print("repeat (not live):", post("/repeat").json()["resent_to_glasses"])

asyncio.run(glasses())
cues = requests.get(f"{RUN}/cues", params={"after": 0}, headers=K).json()
print("phone poll cues:", [c["text"] for c in cues["cues"]], "| glasses_live now:", cues["state"]["glasses_live"])
for i in range(3):
    r = requests.post(f"{API}/attempts/{A['id']}/frame", params={"heading": 90 + i, "steps": 10 + i}, data=os.urandom(4000), headers={**K, "Content-Type": "image/jpeg"})
s = requests.get(f"{API}/attempts/{A['id']}/status", headers=UA).json()
print("after 3 phone frames: phone", s["phone_frames"], "glasses", s["glasses_frames"], "last motion", s["last_motion"])
print("help:", post("/help").status_code)
print("end:", st(post("/end")), "| start after end:", post("/start").status_code, "| help after end:", post("/help").status_code, "| message after end:", requests.post(f"{API}/attempts/{A['id']}/message", json={"text": "hi"}, headers=UA).status_code)
final = requests.get(RUN, headers=K).json()["state"]
print("final:", final["status"], "ended_at set:", bool(final["ended_at"]), "started_at set:", bool(final["started_at"]))
