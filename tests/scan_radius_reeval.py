"""READ-ONLY: replays a scan-route attempt's logged vision results/poses through the cue policy in memory, with and without the scan flag; writes nothing."""
import asyncio
import sys
from datetime import datetime
sys.path.insert(0, "/app/backend")
from cue_policy import PolicyState, alignment, decide, pre_cues  # noqa: E402
from cue_runner import _cp_positions  # noqa: E402
from corrections import is_scan  # noqa: E402
from db import db  # noqa: E402

ATTEMPT = sys.argv[1] if len(sys.argv) > 1 else "8b145984-1d5d-4fcc-a5f9-634db52a4a07"


def ts(iso):
    return datetime.fromisoformat(iso).timestamp()


def run(events, ex, version, cps, scan, flag, t0):
    state, out, trail = PolicyState(), [], []
    for e in events:
        if e.get("pos_x") is not None and e.get("pos_z") is not None:
            trail.append((e["pos_x"], e["pos_z"]))
        if e["type"] in ("start", "resume"):
            kind = {"type": "running"}
        elif e["type"] == "vision":
            kind = {"type": "vision", "result": e.get("result") or {}}
        elif e["type"] == "vision_error":
            kind = {"type": "vision_error", "reason": e.get("reason")}
        else:
            continue
        now = ts(e["t"])
        s = {k: e.get(k) for k in ("pos_x", "pos_z", "heading_deg", "depth_left", "depth_centre", "depth_right")}
        snap = {**s, "origin": trail[0] if trail else None, "align": alignment(trail, scan), "cp_positions": cps, "last_frame_at": now}
        if flag:
            snap["scan"] = True
        cue, state = decide(state, kind, ex, version, snap, now)
        if cue is not None:
            out.extend((now, p) for p in pre_cues(cue))
            out.append((now, cue))
    return [(round(t - t0, 1), c.checkpoint, c.details.get("by"), c.details.get("distance_m")) for t, c in out if c.spoken and c.checkpoint]


async def main():
    a = await db.attempts.find_one({"id": ATTEMPT}, {"_id": 0})
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0})
    route = await db.routes.find_one({"id": ex["route_id"]}, {"_id": 0, "name": 1})
    version = await db.route_versions.find_one({"route_id": ex["route_id"], "version": a["route_version"]}, {"_id": 0})
    events = await db.attempt_events.find({"attempt_id": a["id"]}, {"_id": 0}).sort("seq", 1).to_list(100000)
    cps, scan = await _cp_positions(version), await is_scan(version)
    t0 = ts(events[0]["t"])
    print(f"attempt {a['id']} | route {route['name']} v{a['route_version']} | scan {scan} | checkpoints {[c['name'] for c in sorted(version['checkpoints'], key=lambda c: c['order'])]} | positions {cps}")
    print(f"events {len(events)}, vision {sum(e['type'] == 'vision' for e in events)}, poses {sum(e.get('pos_x') is not None for e in events)}")
    logged = [(round(ts(e['t']) - t0, 1), e["checkpoint"], (e.get("details") or {}).get("by")) for e in events if e["type"] == "cue" and e.get("spoken") and e.get("checkpoint")]
    print("LOGGED (what happened)", logged)
    print("OLD policy (1.0 m)", run(events, ex, version, cps, scan, False, t0))
    print("NEW policy (scan 1.5 m)", run(events, ex, version, cps, scan, True, t0))


asyncio.run(main())
