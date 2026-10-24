"""Builds the two kept Phase 10 review demos through the real flows (needs CUE_TEST_HOOK=1 while building), then checks them.
  python3 review_demo.py build    teach walk + save (3D route), builder route (2D), one finished run on each
  python3 review_demo.py check    header vs event log, error states, run-API leak check (temporary attempts deleted)
"""
import asyncio
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import requests
import websockets

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")
import teach_walk_sim as tw  # noqa: E402

API, WSS, UA = tw.API, tw.WSS, tw.UA
STATE = Path("/app/tests/.review_demo.json")
GOAL = "Review demo (synthetic)"


def post(p, **kw):
    r = requests.post(f"{API}{p}", headers={**UA, **kw.pop("headers", {})}, timeout=60, **kw)
    return r.json() if r.content else {}


def ent(label, rel="ahead", band="near", conf=0.8):
    return {"label": label, "relation": rel, "distance_band": band, "confidence": conf}


def result(**r):
    return {"checkpoint_match": None, "on_route": True, "new_entities": [], "uncertain": False, "unusable": False, **r}


def assign(route_id, style):
    client = [c for c in requests.get(f"{API}/clients", headers=UA).json() if c["display_name"] == "Client A (synthetic)"][0]
    body = {"client_id": client["id"], "goal": GOAL, "cue_style": style, "stay_silent_on_route": False, "no_repeat": True,
            "stop_rule": "If you feel unsure, stop, press Help and wait for my call."}
    return post(f"/routes/{route_id}/exercises", json=body)


async def run_script(att, key, cps, script, mover):
    """Executes timed actions on a running attempt while `mover` keeps frames (and pose or steps) flowing."""
    aid, k = att["id"], {"X-Stream-Key": key}
    hook = f"/test-hooks/attempts/{aid}/vision"
    post(hook, json={"type": "vision_error"})
    state = {"paused": False, "stop": False}
    post(f"/run/{aid}/start", headers=k)
    mover_task = asyncio.create_task(mover(state))
    t0 = time.time()
    for t, action, arg in script:
        await asyncio.sleep(max(0, t0 + t - time.time()))
        if action == "vision":
            await asyncio.to_thread(post, hook, json={"result": result(**arg)})
        elif action == "error":
            await asyncio.to_thread(post, hook, json={"type": "vision_error"})
        elif action == "help":
            await asyncio.to_thread(post, f"/run/{aid}/help", headers=k)
        elif action == "message":
            await asyncio.to_thread(post, f"/attempts/{aid}/message", json={"text": arg})
        elif action in ("pause", "resume", "end"):
            state["paused"] = action == "pause"
            await asyncio.to_thread(post, f"/run/{aid}/{action}", headers=k)
    state["stop"] = True
    await mover_task


def script_for(cps):
    c1, c2 = cps[0]["name"], cps[1]["name"]
    return [
        (1, "vision", {}),
        (2.5, "vision", {"checkpoint_match": c1}),
        (5, "vision", {"checkpoint_match": c1}),
        (9, "vision", {"new_entities": [ent("chair")]}),
        (11, "vision", {"new_entities": [ent("chair")]}),
        (13, "vision", {"new_entities": [ent("sign stand", "left", "mid", 0.45)]}),
        (14, "help", None),
        (15, "vision", {"uncertain": True}),
        (16, "message", "Keep the wall on your left."),
        (17, "vision", {"unusable": True}),
        (18, "vision", {"unusable": True}),
        (19, "error", None),
        (20, "pause", None),
        (24, "resume", None),
        (26, "vision", {}),
        (30, "vision", {"checkpoint_match": c2}),
        (33, "vision", {"new_entities": [ent("cart", "right", "far", 0.9)]}),
        (34, "vision", {"new_entities": [ent("cart", "right", "far", 0.9)]}),
        (36, "end", None),
    ]


def walk_xz(d):
    return (0.0, -d) if d <= 10 else (d - 10, -10.0)


async def build_3d():
    await tw.walk("Review demo route 3D (synthetic)")
    st = json.loads(tw.STATE.read_text()); s = st["session"]; rid = s["route_id"]
    for c in requests.get(f"{API}/routes/{rid}", headers=UA).json()["checkpoints"]:
        if c["needs_photo"]:
            r = requests.post(f"{API}/checkpoints/{c['id']}/photo", files={"file": ("e.jpg", tw.EMPTY, "image/jpeg")}, headers=UA).json()
            print("End photo:", r["ai_status"])
        post(f"/checkpoints/{c['id']}/approve")
    print("save:", post(f"/teach/{s['id']}/save"))
    tw.STATE.unlink()
    cps = requests.get(f"{API}/routes/{rid}/versions", headers=UA).json()[0]["checkpoints"]
    made = assign(rid, "standard")
    att, key = made["attempt"], made["key"]
    origin = (2.0, -1.0)

    async def mover(state):
        d = 0.0
        async with websockets.connect(f"{WSS}/ws/ingest/{att['stream_id']}?key={key}", additional_headers=UA) as ws:
            await ws.recv()
            i = 0
            while not state["stop"]:
                if not state["paused"]:
                    d += 0.5 * 0.2
                x, z = walk_xz(d)
                fwd = (0, 0, -1) if d <= 10 else (1, 0, 0)
                M = tw.pose(np.array([origin[0] + x, 0.0, origin[1] + z]), fwd)
                await ws.send(json.dumps({"type": "phone", "ar_tracking": "normal", "ar_pose": M.flatten(order="F").tolist(), "heading_deg": 0.0 if d <= 10 else 90.0, "ts_capture_ms": i * 200}))
                if i % 2 == 0:
                    await ws.send(tw.EMPTY)
                i += 1
                await asyncio.sleep(0.2)
    await run_script(att, key, cps, script_for(cps), mover)
    return {"route_id": rid, "attempt_id": att["id"], "exercise_id": made["exercise"]["id"], "key": key, "session_id": s["id"]}


async def build_2d():
    route = post("/routes", json={"name": "Review demo route 2D (synthetic)"})
    for name, text in (("Front door", "Heavy glass door with a push bar at waist height."), ("Lift lobby", "Two lifts on the right with a raised call button.")):
        cp = post(f"/routes/{route['id']}/checkpoints")
        r = requests.post(f"{API}/checkpoints/{cp['id']}/photo", files={"file": ("e.jpg", tw.EMPTY, "image/jpeg")}, headers=UA).json()
        print(f"photo {name}:", r["ai_status"])
        requests.patch(f"{API}/checkpoints/{cp['id']}", json={"name": name, "landmark_text": text}, headers=UA)
        post(f"/checkpoints/{cp['id']}/approve")
    v = post(f"/routes/{route['id']}/save")
    print("2D route saved: v", v["version"], "memory:", v["memory_id"])
    made = assign(route["id"], "minimal")
    att, key = made["attempt"], made["key"]

    async def mover(state):
        walked, steps = 0.0, 0
        while not state["stop"]:
            if not state["paused"]:
                walked += 1.0
                steps = int(walked * 1.4)
            heading = 2.0 if walked <= 12 else 91.0
            await asyncio.to_thread(requests.post, f"{API}/attempts/{att['id']}/frame", params={"heading": heading, "steps": steps}, data=tw.EMPTY,
                                    headers={**UA, "X-Stream-Key": key, "Content-Type": "image/jpeg"}, timeout=30)
            await asyncio.sleep(0.8)
    await run_script(att, key, v["checkpoints"], script_for(v["checkpoints"]), mover)
    return {"route_id": route["id"], "attempt_id": att["id"], "exercise_id": made["exercise"]["id"], "key": key}


async def build():
    d3 = await build_3d()
    d2 = await build_2d()
    STATE.write_text(json.dumps({"3d": d3, "2d": d2}))
    print(json.dumps({k: v["attempt_id"] for k, v in (("3d", d3), ("2d", d2))}))


def expected_from_events(aid):
    ev = requests.get(f"{API}/attempts/{aid}/events?limit=1000", headers=UA).json()
    cues = [e for e in ev if e["type"] == "cue"]
    routine = {"on_route_silent", "nothing_to_say"}
    return {
        "cues_spoken": sum(c["spoken"] for c in cues),
        "cues_suppressed": sum(not c["spoken"] and c["suppressed_reason"] not in routine for c in cues),
        "routine_hidden": sum(not c["spoken"] and c["suppressed_reason"] in routine for c in cues),
        "checkpoints_reached": len({c["checkpoint"] for c in cues if c["spoken"] and c["checkpoint"]}),
        "help_count": sum(e["type"] == "help" for e in ev),
    }


async def check():
    from db import db
    st = json.loads(STATE.read_text())
    for name, d in st.items():
        t = time.time(); r = requests.get(f"{API}/attempts/{d['attempt_id']}/review", headers=UA); ms = int((time.time() - t) * 1000)
        rv = r.json(); h, items = rv["header"], rv["timeline"]
        exp = expected_from_events(d["attempt_id"])
        from_timeline = {"cues_spoken": sum(i["category"] == "spoken" for i in items), "cues_suppressed": sum(i["category"] == "suppressed" for i in items),
                         "checkpoints_reached": sum(i["kind"] == "checkpoint" for i in items), "help_count": sum(i["kind"] == "help" for i in items)}
        bad = [k for k in exp if h[k] != exp[k]] + [k for k in from_timeline if h[k] != from_timeline[k]]
        print(f"{name.upper()} {r.status_code} in {ms} ms | {h['client']} | {h['route']} · v{h['version']} | elapsed {h['elapsed_seconds']} s | reached {h['checkpoints_reached']} of {h['checkpoints_total']} | help {h['help_count']} | spoken {h['cues_spoken']} · suppressed {h['cues_suppressed']} | routine hidden {h['routine_hidden']}")
        print(f"  Q-46 header vs event log/timeline mismatches: {len(bad)} {bad}")
        print("  reasons:", sorted({i["reason"] for i in items if i["reason"]}))
        print("  kinds:", sorted({i["kind"] for i in items}), "| dots:", sum(1 for i in items if i["pos"]), "| path:", {k: (v if not isinstance(v, (list, dict)) else len(v)) for k, v in rv["path"].items()})
        if not d.get("key"):
            continue
        pub = requests.get(f"{API}/run/{d['attempt_id']}", headers={**UA, "X-Stream-Key": d["key"]}).text + requests.get(f"{API}/run/{d['attempt_id']}/cues", headers={**UA, "X-Stream-Key": d["key"]}).text
        print("  JRN-147 run API mentions trail/pose/motion/review:", any(w in pub for w in ('"trail"', "pos_x", '"motion"', "would_have_said", "timeline")))
    ex2 = st["2d"]["exercise_id"]
    a1, a2 = post(f"/exercises/{ex2}/attempts"), post(f"/exercises/{ex2}/attempts")
    print("ERRORS: not started:", requests.get(f"{API}/attempts/{a1['attempt']['id']}/review", headers=UA).json(), "| unknown:", requests.get(f"{API}/attempts/nope/review", headers=UA).json())
    k = {"X-Stream-Key": a2["key"]}
    post(f"/run/{a2['attempt']['id']}/start", headers=k); await asyncio.sleep(1); post(f"/run/{a2['attempt']['id']}/end", headers=k)
    print("  no-path attempt path:", requests.get(f"{API}/attempts/{a2['attempt']['id']}/review", headers=UA).json()["path"])
    tmp = {"not_started": a1["attempt"]["id"], "no_path": a2["attempt"]["id"]}
    Path("/app/tests/.review_tmp.json").write_text(json.dumps(tmp))
    print("temporary attempts (delete with `cleanup-tmp`):", tmp)


async def cleanup_tmp():
    from db import db
    tmp = json.loads(Path("/app/tests/.review_tmp.json").read_text())
    ids = list(tmp.values())
    print("deleted attempts:", (await db.attempts.delete_many({"id": {"$in": ids}})).deleted_count, "| events:", (await db.attempt_events.delete_many({"attempt_id": {"$in": ids}})).deleted_count)
    Path("/app/tests/.review_tmp.json").unlink()


asyncio.run({"build": build, "check": check, "cleanup-tmp": cleanup_tmp}[sys.argv[1]]())
