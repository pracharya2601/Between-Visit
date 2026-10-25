"""Phase 19 diagnosis (read-only on the policy): one v1 replay, then the same logged vision results through the policy
in memory, as-is vs. with a 'picture match must be within 3 m of the checkpoint position' guard. Deletes the replay."""
import asyncio
import math
import sys
from datetime import datetime

import requests

sys.path.insert(0, "/app/backend")
sys.path.insert(0, "/app/tests")
from cue_policy import PolicyState, alignment, decide, to_route  # noqa: E402
from cue_runner import _cp_positions  # noqa: E402
from db import db  # noqa: E402
from replay_check import API, ROUTE, wait_end  # noqa: E402


def ts(iso):
    return datetime.fromisoformat(iso).timestamp()


async def run(on, guard_m=None):
    aid = requests.post(f"{API}/routes/{ROUTE}/replays", json={"on": on}).json()["attempt_id"]
    wait_end(aid)
    a = await db.attempts.find_one({"id": aid}, {"_id": 0})
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0})
    version = await db.route_versions.find_one({"route_id": ROUTE, "version": a["route_version"]}, {"_id": 0})
    cps = await _cp_positions(version)
    names = [c["name"] for c in sorted(version["checkpoints"], key=lambda c: c["order"])]
    events = await db.attempt_events.find({"attempt_id": aid}, {"_id": 0}).sort("seq", 1).to_list(1000)
    trail = [(p["x"], p["z"]) for p in a.get("trail") or []]
    out = {}
    for g in (None, guard_m):
        state, said = PolicyState(), []
        for e in events:
            if e["type"] not in ("start", "resume", "vision"):
                continue
            now = ts(e["t"])
            if e["type"] != "vision":
                _, state = decide(state, {"type": "running"}, ex, version, {}, now)
                continue
            r = dict(e.get("result") or {})
            al = alignment(trail[:1] or [(0, 0)])
            if g and r.get("checkpoint_match") in names and e.get("pos_x") is not None:
                p = cps.get(names.index(r["checkpoint_match"]))
                x, z = to_route(al, e["pos_x"], e["pos_z"])
                if p and math.hypot(x - p[0], z - p[1]) > g:
                    r["checkpoint_match"] = None
            s = {"pos_x": e.get("pos_x"), "pos_z": e.get("pos_z"), "heading_deg": e.get("heading_deg"), "depth_left": e.get("depth_left"),
                 "depth_centre": e.get("depth_centre"), "depth_right": e.get("depth_right"), "align": al, "cp_positions": cps, "last_frame_at": now}
            cue, state = decide(state, {"type": "vision", "result": r}, ex, version, s, now)
            if cue and cue.spoken:
                said.append(cue.text[:40])
        out["guard" if g else "as-is"] = said
    await db.attempt_events.delete_many({"attempt_id": aid})
    await db.attempts.delete_one({"id": aid})
    return out


async def main():
    for on in ("v1", "v1", "latest"):
        for k, said in (await run(on, 3.0)).items():
            print(on, k, said)


asyncio.run(main())
