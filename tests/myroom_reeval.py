"""READ-ONLY: replays the My room attempt's logged vision results through the current cue policy in memory; writes nothing."""
import asyncio
import sys
from datetime import datetime
sys.path.insert(0, "/app/backend")
from cue_policy import PolicyState, decide, pre_cues  # noqa: E402
from cue_runner import _cp_positions  # noqa: E402
from db import db  # noqa: E402

PREFIX = sys.argv[1] if len(sys.argv) > 1 else "c5779642"


def ts(iso):
    return datetime.fromisoformat(iso).timestamp()


async def main():
    a = await db.attempts.find_one({"id": {"$regex": f"^{PREFIX}"}}, {"_id": 0})
    ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0})
    route = await db.routes.find_one({"id": ex["route_id"]}, {"_id": 0, "name": 1})
    version = await db.route_versions.find_one({"route_id": ex["route_id"], "version": a["route_version"]}, {"_id": 0})
    events = await db.attempt_events.find({"attempt_id": a["id"]}, {"_id": 0}).sort("seq", 1).to_list(100000)
    cps = await _cp_positions(version)
    trail = a.get("trail") or []
    origin = (trail[0]["x"], trail[0]["z"]) if trail else None
    print(f"attempt {a['id']} | route {route['name']} v{a['route_version']} | checkpoints {[c['name'] for c in sorted(version['checkpoints'], key=lambda c: c['order'])]} | positions {cps or 'none'}")
    old = [e for e in events if e["type"] == "cue"]
    t0 = ts(events[0]["t"])
    old_pauses = [(round(ts(e['t']) - t0, 1), e.get("reason")) for e in old if e["spoken"] and e.get("priority") == 0]
    old_cps = [(round(ts(e['t']) - t0, 1), e["checkpoint"]) for e in old if e["spoken"] and e.get("checkpoint")]
    state, new = PolicyState(), []
    for e in events:
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
        cue, state = decide(state, kind, ex, version, {**s, "origin": origin, "cp_positions": cps, "last_frame_at": now}, now)
        if cue is not None:
            new.extend((now, p) for p in pre_cues(cue))
            new.append((now, cue))
    new_pauses = [(round(t - t0, 1), c.trigger) for t, c in new if c.spoken and c.priority == 0]
    new_cps = [(round(t - t0, 1), c.checkpoint, c.details.get("by")) for t, c in new if c.spoken and c.checkpoint]
    missed = [(round(t - t0, 1), c.checkpoint) for t, c in new if c.suppressed_reason == "checkpoint_skipped"]
    n_vis = sum(e["type"] == "vision" for e in events)
    n_unusable = sum(e["type"] == "vision" and (e.get("result") or {}).get("unusable") for e in events)
    print(f"vision results {n_vis} (unusable {n_unusable}), vision errors {sum(e['type'] == 'vision_error' for e in events)}")
    print("OLD pauses", len(old_pauses), old_pauses)
    print("NEW pauses", len(new_pauses), new_pauses)
    print("OLD checkpoints", old_cps)
    print("NEW checkpoints", new_cps)
    print("NEW missed", missed)
    print("NEW picture_too_far silences", sum(c.suppressed_reason == "picture_too_far" for _, c in new))
    print("NEW unusable_frame silences", sum(c.suppressed_reason == "unusable_frame" for _, c in new))


asyncio.run(main())
