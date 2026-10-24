"""Q-49: a phone-camera run whose camera starts at 3 s hears no pause line in the first 15 s. Needs run_check_data setup (uses attempts[1])."""
import json
import time

import requests

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
UA = {"User-Agent": "between-visit-check/1.0"}
IMG = "https://static.prod-images.emergentagent.com/jobs/b64ebf54-447e-4e98-bd8c-1cc6c532d0bc/images/b86f4f5409828025d4be324127f88d16e823fcc0b3cf9269bbb184b619bcbfb7.jpeg"
JPEG = requests.get(IMG, timeout=30).content
A = json.load(open("/app/tests/.run_check.json"))["attempts"][1]
K = {**UA, "X-Stream-Key": A["key"]}

requests.post(f"{API}/run/{A['id']}/start", headers=K)
t0 = time.time()
time.sleep(3)
while time.time() - t0 < 15.5:
    requests.post(f"{API}/attempts/{A['id']}/frame", params={"heading": 10, "steps": int(time.time() - t0)}, data=JPEG, headers={**K, "Content-Type": "image/jpeg"})
    time.sleep(max(0, 1 - (time.time() - t0) % 1))
ev = requests.get(f"{API}/attempts/{A['id']}/events", headers=UA).json()
cues = [e for e in ev if e["type"] == "cue"]
pauses = [e for e in cues if e["priority"] == 0 and e["spoken"]]
motion = requests.get(f"{API}/attempts/{A['id']}/review", headers=UA).json()["path"]
print(f"Q-49: pause lines in first 15 s: {len(pauses)} | vision events {sum(e['type'] in ('vision', 'vision_error') for e in ev)} | cue events {len(cues)} | reasons {sorted({c['suppressed_reason'] or 'spoken' for c in cues})}")
print("motion samples -> review path:", motion["mode"], motion.get("source"), len(motion.get("trail", [])), "points")
requests.post(f"{API}/run/{A['id']}/end", headers=K)
