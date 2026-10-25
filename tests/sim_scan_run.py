"""Phase 18: simulated run on a scan route with the ARKit frame rotated 70° (and shifted) from the scan.
Uses the real pipeline: attempt trail points as ingest stores them, cue_runner.handle (policy + position rule), then the review path.
  python3 sim_scan_run.py ROUTE_ID     prints alignment angle error, position-rule timing, review-path fit; deletes the exercise/attempt
"""
import asyncio
import math
import sys
from dataclasses import replace
import requests

sys.path.insert(0, "/app/backend")
import cue_runner  # noqa: E402
from cue_policy import alignment  # noqa: E402
from db import db  # noqa: E402
from models import now_iso  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
ROT, OFF = math.radians(70), (5.0, -2.0)


def to_arkit(x, z):
    """Route frame → a phone frame rotated 70° and shifted, like an ARKit session that started facing elsewhere."""
    c, s = math.cos(ROT), math.sin(ROT)
    return OFF[0] + c * x - s * z, OFF[1] + s * x + c * z


def walk(points, step=0.25):
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        d = math.dist(a, b)
        for i in range(1, int(d / step) + 1):
            out.append((a[0] + (b[0] - a[0]) * i * step / d, a[1] + (b[1] - a[1]) * i * step / d))
    return out


def seg_dist(p, a, b):
    ax, az, bx, bz = *a, *b
    t = max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - az) * (bz - az)) / (((bx - ax) ** 2 + (bz - az) ** 2) or 1)))
    return math.dist(p, (ax + t * (bx - ax), az + t * (bz - az)))


async def main(route_id):
    mem = requests.get(f"{API}/routes/{route_id}/memory").json()
    cps = sorted(mem["checkpoints"], key=lambda c: c["order"])
    route = [(c["position"]["x"], c["position"]["z"]) for c in cps]
    print("memory endpoint checkpoints:", [(c["name"], c["position"]["x"], c["position"]["z"]) for c in cps])
    client = await db.clients.find_one({"display_name": "Client A (synthetic)"}, {"_id": 0, "id": 1})
    r = requests.post(f"{API}/routes/{route_id}/exercises", json={"client_id": client["id"], "goal": "Sim scan run", "stop_rule": "Stop if unsure", "cue_style": "minimal"})
    aid, ex_id = r.json()["attempt"]["id"], r.json()["exercise"]["id"]
    now = now_iso()
    await db.attempts.update_one({"id": aid}, {"$set": {"status": "running", "started_at": now, "running_since": now, "trail": []}})
    path = walk(route)
    walked, spoken, early = 0.0, [], None
    heading = lambda a, b: math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1]))) + math.degrees(ROT)
    for i, p in enumerate(path):
        x, z = to_arkit(*p)
        walked = i * 0.25
        await db.attempts.update_one({"id": aid}, {"$push": {"trail": {"x": x, "z": z, "t": now_iso()}}})
        h = heading(path[max(0, i - 1)], p) if i else heading(p, path[1])
        if i == 0:
            await cue_runner.handle(aid, {"type": "vision", "result": {"checkpoint_match": cps[0]["name"], "on_route": True, "new_entities": [], "uncertain": False, "unusable": False}},
                                    {"pos_x": x, "pos_z": z, "heading_deg": h})
        elif i == 2:
            cue_runner.STATES[aid] = replace(cue_runner.STATES[aid], last_spoken_at=None)
            cx, cz = to_arkit(*route[1])
            await cue_runner.handle(aid, {"type": "vision", "result": {"checkpoint_match": None, "on_route": True, "new_entities": [], "uncertain": False, "unusable": False}},
                                    {"pos_x": cx, "pos_z": cz, "heading_deg": h})
            early = [c for c in await db.attempt_events.find({"attempt_id": aid, "type": "cue"}, {"_id": 0}).to_list(50) if c.get("checkpoint") == cps[1]["name"]]
        elif i % 2 == 0:
            cue_runner.STATES[aid] = replace(cue_runner.STATES[aid], last_spoken_at=None)  # the sim walks faster than real time; skip the 3 s spacing
            await cue_runner.handle(aid, {"type": "vision", "result": {"checkpoint_match": None, "on_route": True, "new_entities": [], "uncertain": False, "unusable": False}},
                                    {"pos_x": x, "pos_z": z, "heading_deg": h})
    doc = await db.attempts.find_one({"id": aid}, {"_id": 0, "trail": 1})
    trail = [(p["x"], p["z"]) for p in doc["trail"]]
    al = alignment(trail, True)
    i15 = next(i for i, p in enumerate(trail) if math.dist(p, trail[0]) >= 1.5)
    fx = al[2] * (trail[i15][0] - trail[0][0]) - al[3] * (trail[i15][1] - trail[0][1])
    fz = al[3] * (trail[i15][0] - trail[0][0]) + al[2] * (trail[i15][1] - trail[0][1])
    route_dir = math.degrees(math.atan2(route[1][0] - route[0][0], -(route[1][1] - route[0][1])))
    print(f"Q-80 angle error after alignment: {abs(math.degrees(math.atan2(fx, -fz)) - route_dir):.2f}° (first 1.5 m vs Entrance facing)")
    print("before 1.5 m (pose placed on checkpoint 2 at 0.5 m walked): checkpoint cues =", [(c["checkpoint"], (c.get("details") or {}).get("by")) for c in early])
    cues = await db.attempt_events.find({"attempt_id": aid, "type": "cue", "spoken": True}, {"_id": 0}).sort("seq", 1).to_list(200)
    print("checkpoints reached:", [(c["checkpoint"], (c.get("details") or {}).get("by"), (c.get("details") or {}).get("distance_m")) for c in cues if c.get("checkpoint")])
    await db.attempts.update_one({"id": aid}, {"$set": {"status": "ended", "ended_at": now_iso(), "running_since": None}})
    rv = requests.get(f"{API}/attempts/{aid}/review").json()
    run = rv["path"]["run_trail"]
    fit = max(min(seg_dist((p[0], p[2]), a, b) for a, b in zip(route, route[1:])) for p in run)
    print(f"review path: mode {rv['path']['mode']} aligned {rv['path']['aligned']} | {len(run)} points | max distance from the placed route {fit:.3f} m | model {rv['path']['scene']['model_label']}")
    raw_fit = max(min(seg_dist((p[0] - trail[0][0], p[1] - trail[0][1]), a, b) for a, b in zip(route, route[1:])) for p in trail)
    print(f"(without rotation it would be {raw_fit:.2f} m off)")
    print("attempt:", aid, "exercise:", ex_id)
    cue_runner.STATES.pop(aid, None)
    cue_runner.CONTEXT.pop(aid, None)


asyncio.run(main(sys.argv[1]))
