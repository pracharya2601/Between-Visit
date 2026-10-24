import io, json, sys, time, urllib.request
import requests
from PIL import Image

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
H = {"User-Agent": "between-visit-check/1.0"}
CORRIDOR, PERSON = sys.argv[1], sys.argv[2]


def fetch(url):
    return requests.get(url, headers=H, timeout=30).content


def big_with_gps(jpeg):
    img = Image.open(io.BytesIO(jpeg)).convert("RGB").resize((3000, 2012))
    exif = Image.Exif()
    exif[0x010F] = "TestCam"
    exif[0x8825] = {2: (37.0, 46.0, 30.0), 1: "N"}
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif.tobytes(), quality=90)
    return out.getvalue()


def call(method, path, **kw):
    r = requests.request(method, f"{API}{path}", headers=H, timeout=60, **kw)
    return r


route = call("POST", "/routes").json()
rid = route["id"]
call("PATCH", f"/routes/{rid}", json={"name": "Check route (synthetic)"})
cps = [call("POST", f"/routes/{rid}/checkpoints").json() for _ in range(3)]

src = big_with_gps(fetch(CORRIDOR))
print("input:", Image.open(io.BytesIO(src)).size, "has GPS exif:", 0x8825 in Image.open(io.BytesIO(src)).getexif())
t = time.time()
r = call("POST", f"/checkpoints/{cps[0]['id']}/photo", files={"file": ("corridor.jpg", src, "image/jpeg")}).json()
print(f"corridor -> {r['ai_status']} in {time.time()-t:.1f}s: {r['checkpoint']['landmark_text']!r} ({len(r['checkpoint']['landmark_text'].split())} words) ai_suggested={r['checkpoint']['ai_suggested']}")
stored = Image.open(io.BytesIO(fetch(API.rsplit('/api', 1)[0] + r["checkpoint"]["photo_url"])))
print("stored photo:", stored.size, "ratio in/out:", round(3000 / 2012, 3), round(stored.width / stored.height, 3), "exif tags:", dict(stored.getexif()))

t = time.time()
r = call("POST", f"/checkpoints/{cps[1]['id']}/photo", files={"file": ("person.jpg", fetch(PERSON), "image/jpeg")}).json()
print(f"person -> {r['ai_status']} in {time.time()-t:.1f}s: message={r['message']!r} photo_url={r['checkpoint']['photo_url']} text={r['checkpoint']['landmark_text']!r}")

r = call("POST", f"/checkpoints/{cps[1]['id']}/photo", files={"file": ("notes.txt", b"hello", "text/plain")})
print("text file ->", r.status_code, r.json()["detail"])
r = call("POST", f"/checkpoints/{cps[1]['id']}/photo", files={"file": ("big.jpg", b"\xff" * (16 * 1024 * 1024), "image/jpeg")})
print("16 MB file ->", r.status_code, r.text[:80])

# Give checkpoints 2 and 3 the corridor photo too (reusing an AI call each), then name + approve
for cp in cps[1:]:
    call("POST", f"/checkpoints/{cp['id']}/photo", files={"file": ("c.jpg", fetch(CORRIDOR), "image/jpeg")})
for i, cp in enumerate(cps, 1):
    call("PATCH", f"/checkpoints/{cp['id']}", json={"name": f"Point {i}"})
print("save with unapproved ->", call("POST", f"/routes/{rid}/save").json()["detail"])
for cp in cps:
    print("approve", call("POST", f"/checkpoints/{cp['id']}/approve").json()["approved"])
v1 = call("POST", f"/routes/{rid}/save").json()
print("saved version", v1["version"], "author", v1["author"], "snapshot names", [c["name"] for c in v1["checkpoints"]])

order = call("POST", f"/checkpoints/{cps[2]['id']}/move", json={"direction": "up"}).json()
print("after move: names", [c["name"] for c in order], "approved", [c["approved"] for c in order])
e = call("PATCH", f"/checkpoints/{cps[0]['id']}", json={"landmark_text": "Edited landmark: handrail ends at the fire door."}).json()
print("after text edit: approved", e["approved"], "ai_suggested", e["ai_suggested"])
print("save blocked ->", call("POST", f"/routes/{rid}/save").json()["detail"])
call("POST", f"/checkpoints/{cps[0]['id']}/approve")
v2 = call("POST", f"/routes/{rid}/save").json()
print("saved version", v2["version"])
versions = call("GET", f"/routes/{rid}/versions").json()
print("v1 unchanged:", versions[0] == v1, "| v2 order:", [c["name"] for c in versions[1]["checkpoints"]])
print("route list entry:", [x for x in call("GET", "/routes").json() if x["id"] == rid][0])
print("ROUTE_ID", rid)
