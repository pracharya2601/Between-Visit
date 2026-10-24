"""Phase 9 relevance-policy checks.
  python3 cue_policy_check.py replay   pure replays of JRN-117..132, 3x for determinism
  python3 cue_policy_check.py e2e      temporary attempt over public wss (needs CUE_TEST_HOOK=1 on the backend), then deletes its data
"""
import asyncio
import io
import json
import sys
import time

sys.path.insert(0, "/app/backend")
from cue_policy import PolicyState, decide  # noqa: E402

T0 = 1_000_000.0
VER = {"version": 3, "known_entities": ["bench", "Plant pot"], "checkpoints": [
    {"order": 1, "name": "Entrance doors", "landmark_text": "Glass double doors with a steel handrail on the right."},
    {"order": 2, "name": "Handrail end", "landmark_text": "The handrail ends at a square pillar."},
    {"order": 3, "name": "Reception desk", "landmark_text": "Long wooden desk facing the doors."},
]}


def ex(style="minimal", silent=True, no_repeat=True):
    return {"cue_style": style, "silence_rules": {"stay_silent_on_route": silent, "no_repeat": no_repeat}}


def ent(label, rel="ahead", band="near", conf=0.8):
    return {"label": label, "relation": rel, "distance_band": band, "confidence": conf}


def vis(match=None, on_route=True, ents=(), unusable=False):
    return {"type": "vision", "result": {"checkpoint_match": match, "on_route": on_route, "new_entities": list(ents), "uncertain": False, "unusable": unusable}}


ERR, TICK, STOP, RUN = {"type": "vision_error"}, {"type": "tick"}, {"type": "vision_stopped"}, {"type": "running"}


def replay(steps, exercise):
    """steps: (t, event, sensors-or-None, frame_t-or-None). Frames are assumed to arrive at t unless frame_t is given."""
    state, out = PolicyState(), []
    for t, event, sensors, frame_t in [(0.0, RUN, None, None)] + steps:
        s = {**(sensors or {}), "last_frame_at": T0 + (t if frame_t is None else frame_t)}
        cue, state = decide(state, event, exercise, VER, s, T0 + t)
        if cue is not None:
            out.append((t, cue.text, cue.priority, cue.spoken, cue.suppressed_reason))
    return out


P = "Vision unavailable, please pause."
CASES = {
    "JRN-117 unusable": (ex(), [(1, vis(unusable=True), None, None)],
                         [(1, P, 0, True, None)]),
    "JRN-118 pause_already_sent / re-arm": (ex(), [(1, vis(unusable=True), None, None), (2, vis(unusable=True), None, None), (3, vis(), None, None), (4, vis(unusable=True), None, None)],
                                            [(1, P, 0, True, None), (2, P, 0, False, "pause_already_sent"), (3, "", None, False, "on_route_silent"), (4, P, 0, True, None)]),
    "JRN-119 no frames 2 s": (ex(), [(1, vis(), None, None), (2, TICK, None, 1.9), (3, TICK, None, 1.9), (4, TICK, None, 1.9), (5, TICK, None, 1.9)],
                              [(1, "", None, False, "on_route_silent"), (4, P, 0, True, None)]),
    "JRN-120 vision_error for 5 s": (ex(), [(1, vis(), None, None)] + [(t, ERR, None, None) for t in (2, 3, 4, 5)] + [(5.5, TICK, None, None), (6, ERR, None, None), (6.5, TICK, None, None), (7, ERR, None, None)],
                                     [(1, "", None, False, "on_route_silent")] + [(t, "", None, False, "vision_error") for t in (2, 3, 4, 5)] + [(6, P, 0, True, None), (7, P, 0, False, "pause_already_sent")]),
    "JRN-121 checkpoint 1 minimal, again falls through": (ex(), [(1, vis("Entrance doors"), None, None), (5, vis("Entrance doors"), None, None)],
                                                           [(1, "Checkpoint 1: Entrance doors.", 2, True, None), (5, "", None, False, "on_route_silent")]),
    "JRN-122 standard cp2 after cp1": (ex("standard"), [(1, vis("Entrance doors"), None, None), (5, vis("Handrail end"), None, None)],
                                       [(1, "Checkpoint 1: Entrance doors. Glass double doors with a steel handrail on the right.", 2, True, None),
                                        (5, "Checkpoint 2: Handrail end. The handrail ends at a square pillar.", 2, True, None)]),
    "JRN-122 cp3 before cp2 -> no checkpoint cue": (ex("standard"), [(1, vis("Entrance doors"), None, None), (5, vis("Reception desk"), None, None), (9, vis("Handrail end"), None, None)],
                                                    [(1, "Checkpoint 1: Entrance doors. Glass double doors with a steel handrail on the right.", 2, True, None), (5, "", None, False, "on_route_silent"),
                                                     (9, "Checkpoint 2: Handrail end. The handrail ends at a square pillar.", 2, True, None)]),
    "JRN-123 chair ahead 1.4 m": (ex(), [(1, vis(ents=[ent("chair")]), {"depth_centre": 1.4}, None)],
                                  [(1, "Chair ahead, about 1.5 metres.", 1, True, None)]),
    "JRN-124 cart right, no depth, mid": (ex(), [(1, vis(ents=[ent("cart", "right", "mid")]), {"depth_right": None, "depth_centre": 2.0}, None)],
                                         [(1, "Cart on your right, a few steps.", 1, True, None)]),
    "JRN-125 low confidence": (ex(), [(1, vis(ents=[ent("chair", conf=0.5)]), None, None)],
                               [(1, "Chair ahead, close.", 1, False, "low_confidence")]),
    "JRN-126 known entity": (ex(), [(1, vis(ents=[ent("BENCH", "left")]), None, None)],
                             [(1, "Bench on your left, close.", 1, False, "known_entity")]),
    "JRN-127 duplicate with pose": (ex(), [(1, vis(ents=[ent("chair")]), {"pos_x": 0.0, "pos_z": 0.0}, None), (5, vis(ents=[ent("chair")]), {"pos_x": 0.0, "pos_z": -2.0}, None),
                                           (9, vis(ents=[ent("chair")]), {"pos_x": 0.0, "pos_z": -4.0}, None)],
                                    [(1, "Chair ahead, close.", 1, True, None), (5, "Chair ahead, close.", 1, False, "duplicate"), (9, "Chair ahead, close.", 1, True, None)]),
    "JRN-127 duplicate without pose": (ex(), [(1, vis(ents=[ent("chair")]), None, None), (5, vis(ents=[ent("chair")]), None, None), (22, vis(ents=[ent("chair")]), None, None)],
                                       [(1, "Chair ahead, close.", 1, True, None), (5, "Chair ahead, close.", 1, False, "duplicate"), (22, "Chair ahead, close.", 1, True, None)]),
    "JRN-128 no_repeat off": (ex(no_repeat=False), [(1, vis(ents=[ent("chair")]), {"pos_x": 0.0, "pos_z": 0.0}, None), (2, vis(ents=[ent("chair")]), {"pos_x": 0.0, "pos_z": -1.0}, None),
                                                    (5, vis(ents=[ent("chair")]), {"pos_x": 0.0, "pos_z": -2.0}, None)],
                              [(1, "Chair ahead, close.", 1, True, None), (2, "Chair ahead, close.", 1, False, "rate_limited"), (5, "Chair ahead, close.", 1, True, None)]),
    "JRN-129 stay-silent on": (ex(silent=True), [(1, vis(), None, None)],
                               [(1, "", None, False, "on_route_silent")]),
    "JRN-130 On route every 20 s": (ex(silent=False), [(t, vis(), None, None) for t in range(25)],
                                    [(t, "On route.", 2, True, None) if t in (0, 20) else (t, "", None, False, "nothing_to_say") for t in range(25)]),
    "JRN-131 rate-limited checkpoint fires later": (ex(), [(1, vis(ents=[ent("chair")]), None, None), (2, vis("Entrance doors"), None, None), (4.5, vis("Entrance doors"), None, None)],
                                                    [(1, "Chair ahead, close.", 1, True, None), (2, "Checkpoint 1: Entrance doors.", 2, False, "rate_limited"), (4.5, "Checkpoint 1: Entrance doors.", 2, True, None)]),
    "JRN-132 p0 bypasses rate limit": (ex(), [(1, vis(ents=[ent("chair")]), None, None), (2, vis(unusable=True), None, None), (4.5, vis("Entrance doors"), None, None)],
                                       [(1, "Chair ahead, close.", 1, True, None), (2, P, 0, True, None), (4.5, "Checkpoint 1: Entrance doors.", 2, False, "rate_limited")]),
    "extra: nearest then most confident, 1 metre": (ex(), [(1, vis(ents=[ent("sign stand", "left", "far", 0.95), ent("cart", "right", "near", 0.7), ent("chair", "right", "near", 0.9)]), {"depth_right": 1.1, "depth_left": 4.0}, None)],
                                                    [(1, "Chair on your right, about 1 metre.", 1, True, None)]),
    "extra: on_route false -> nothing_to_say": (ex(silent=False), [(1, vis(on_route=False), None, None)],
                                                [(1, "", None, False, "nothing_to_say")]),
    "extra: vision stopped at 30 min": (ex(), [(1, vis(), None, None), (2, STOP, None, None)],
                                        [(1, "", None, False, "on_route_silent"), (2, P, 0, True, None)]),
}


def run_replays():
    runs = [{name: replay(steps, exercise) for name, (exercise, steps, _) in CASES.items()} for _ in range(3)]
    fails = 0
    for name, (_, _, expected) in CASES.items():
        got = runs[0][name]
        ok = [tuple(map(lambda v: float(v) if isinstance(v, int) and not isinstance(v, bool) else v, g)) for g in got] == \
             [tuple(map(lambda v: float(v) if isinstance(v, int) and not isinstance(v, bool) else v, e)) for e in expected]
        fails += not ok
        spoken = [f"t{g[0]:g} \"{g[1]}\" p{g[2]}" for g in got if g[3]]
        silent = sorted({g[4] for g in got if not g[3]})
        print(f"{'PASS' if ok else 'FAIL'} {name}: spoken {spoken or '-'} | silent {silent or '-'}")
        if not ok:
            print("   expected", expected, "\n   got     ", got)
    same = all(json.dumps(r, sort_keys=True) == json.dumps(runs[0], sort_keys=True) for r in runs)
    print(f"DETERMINISM (Q-42): 3 replays identical: {same} | cases {len(CASES)} | failures {fails}")


async def e2e():
    import requests
    import websockets
    from PIL import Image
    from db import db
    from migrations import delete_routes_cascade
    from models import CheckpointSnapshot, Route, RouteVersion

    api = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
    ua = {"User-Agent": "between-visit-check/1.0"}
    buf = io.BytesIO(); Image.new("RGB", (64, 48), (120, 120, 120)).save(buf, "JPEG"); jpeg = buf.getvalue()
    practice = await db.practices.find_one({}, {"_id": 0, "id": 1})
    client_a = await db.clients.find_one({"display_name": "Client A (synthetic)"}, {"_id": 0, "id": 1})
    route = Route(practice_id=practice["id"], name="Cue check (synthetic)", current_version=1)
    cps = [CheckpointSnapshot(id=f"cp{c['order']}", photo_url="/api/photos/none", **{k: c[k] for k in ("order", "name", "landmark_text")}) for c in VER["checkpoints"]]
    await db.routes.insert_one(route.to_mongo())
    await db.route_versions.insert_one(RouteVersion(route_id=route.id, version=1, checkpoints=cps, known_entities=["bench"], author="J. Rivera (synthetic)").to_mongo())
    try:
        body = {"client_id": client_a["id"], "goal": "Cue check (synthetic)", "stop_rule": "Stop and press Help.", "cue_style": "minimal", "stay_silent_on_route": False, "no_repeat": True}
        made = requests.post(f"{api}/routes/{route.id}/exercises", json=body, headers=ua).json()
        aid, sid, key = made["attempt"]["id"], made["attempt"]["stream_id"], made["key"]
        hook = f"{api}/test-hooks/attempts/{aid}/vision"
        k = {**ua, "X-Stream-Key": key}
        print("hook before start:", requests.post(hook, json={"type": "vision_error"}, headers=ua).json())
        guides, sending = [], {"on": True}

        def inject(**result):
            r = {"checkpoint_match": None, "on_route": True, "new_entities": [], "uncertain": False, "unusable": False, **result}
            return requests.post(hook, json={"result": r}, headers=ua).json()

        async with websockets.connect(f"{api.replace('https://', 'wss://')}/ws/ingest/{sid}?key={key}", additional_headers=ua) as ws:
            print("ws first message:", await ws.recv())

            async def recv():
                async for m in ws:
                    if isinstance(m, str):
                        guides.append((time.time(), json.loads(m)))

            async def frames():
                while True:
                    if sending["on"]:
                        await ws.send(jpeg)
                    await asyncio.sleep(0.3)

            tasks = [asyncio.create_task(recv()), asyncio.create_task(frames())]
            await asyncio.sleep(0.5)
            print("start:", requests.post(f"{api}/run/{aid}/start", headers=k).json()["status"])
            script = [("unusable", dict(unusable=True)), ("cp1", dict(checkpoint_match="Entrance doors")), ("chair", dict(new_entities=[ent("chair")])),
                      ("on_route 0.6 s after chair (rate limit)", dict()), ("known bench", dict(new_entities=[ent("bench", "left")]))]
            for i, (label, r) in enumerate(script):
                n = len(guides); inj = inject(**r); await asyncio.sleep(0.6 if i == 2 else 3.2)
                print(f"  inject {label}: guides on GlassCam {[(g['text'], g['priority']) for _, g in guides[n:]] or 'none'}")
            n = len(guides); requests.post(hook, json={"type": "vision_error"}, headers=ua); await asyncio.sleep(0.6)
            print(f"  inject vision_error: guides {[(g['text'], g['priority']) for _, g in guides[n:]] or 'none'}")
            lat = []
            for _ in range(5):
                inject(on_route=False); await asyncio.sleep(0.3)
                n = len(guides); inj = inject(unusable=True)
                for _ in range(40):
                    if len(guides) > n:
                        break
                    await asyncio.sleep(0.025)
                lat.append(round((guides[n][0] - inj["seq"] / 1e9) * 1000) if len(guides) > n else None)
                await asyncio.sleep(0.4)
            print("LATENCY (Q-44) vision event logged -> guide on GlassCam, ms:", lat)
            inject(on_route=False)
            print("pause:", requests.post(f"{api}/run/{aid}/pause", headers=k).json()["status"])
            n = len(guides); cues_before = await db.attempt_events.count_documents({"attempt_id": aid, "type": "cue"})
            p1, p2 = inject(unusable=True), inject(checkpoint_match="Handrail end")
            sending["on"] = False; await asyncio.sleep(3.5)
            print(f"PAUSED: hook logged {p1['logged']}/{p2['logged']}, new cue events {await db.attempt_events.count_documents({'attempt_id': aid, 'type': 'cue'}) - cues_before}, guides {len(guides) - n}")
            print("resume:", requests.post(f"{api}/run/{aid}/resume", headers=k).json()["status"])
            n = len(guides); await asyncio.sleep(3.5)
            print(f"NO FRAMES after resume (3.5 s): guides {[(g['text'], g['priority']) for _, g in guides[n:]]}")
            print("end:", requests.post(f"{api}/run/{aid}/end", headers=k).json()["status"])
            await asyncio.sleep(1.5)
            for t in tasks:
                t.cancel()
        evs = await db.attempt_events.find({"attempt_id": aid}, {"_id": 0}).sort("seq", 1).to_list(1000)
        vis_ids = [e["id"] for e in evs if e["type"] in ("vision", "vision_error")]
        per = {i: sum(1 for e in evs if e["type"] == "cue" and e.get("for_event_id") == i) for i in vis_ids}
        timer_cues = [e for e in evs if e["type"] == "cue" and not e.get("for_event_id")]
        print(f"COVERAGE (Q-43): vision/vision_error events {len(vis_ids)}, without exactly one cue: {sum(v != 1 for v in per.values())} | timer cues {[(c['text'], c['reason']) for c in timer_cues]}")
        spans, paused = [], None
        for e in evs:
            if e["type"] == "pause":
                paused = [e["seq"], None]
            elif e["type"] == "resume" and paused:
                paused[1] = e["seq"]; spans.append(paused)
        print("cues logged while paused:", sum(1 for e in evs if e["type"] == "cue" and any(a < e["seq"] < b for a, b in spans)))
        sp = [e["seq"] / 1e9 for e in evs if e["type"] == "cue" and e["spoken"] and e["priority"]]
        print("OVERLOAD (Q-45): max spoken non-0 cues in any 3 s window:", max(sum(1 for y in sp if x <= y < x + 3) for x in sp))
        print("cue reasons:", {r: sum(1 for e in evs if e["type"] == "cue" and (e["suppressed_reason"] or "spoken") == r) for r in sorted({e["suppressed_reason"] or "spoken" for e in evs if e["type"] == "cue"})})
        print("policy guides logged:", sum(1 for e in evs if e["type"] == "guide" and e.get("reason") == "policy"), "| GlassCam guides received:", len(guides), "| priorities", sorted({g["priority"] for _, g in guides}))
        print("orphan cue events (teach/unknown attempts):", await db.attempt_events.count_documents({"type": "cue", "attempt_id": {"$nin": await db.attempts.distinct("id")}}))
    finally:
        print("CLEANUP:", await delete_routes_cascade([route.id]))


if sys.argv[1] == "replay":
    run_replays()
else:
    asyncio.run(e2e())
