"""Relevance policy: pure, deterministic rules that turn one input into at most one cue. No I/O, no clock."""
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, Optional, Tuple

PAUSE_TEXT = "Vision unavailable, please pause."
ON_ROUTE_TEXT = "On route."
NO_FRAMES_S = 2.0
GRACE_S = 15.0
NO_USABLE_S = 5.0
ON_ROUTE_EVERY_S = 20.0
RATE_LIMIT_S = 3.0
DUP_RADIUS_M = 3.0
DUP_WINDOW_S = 20.0
MIN_CONFIDENCE = 0.6
BAND_M = {"near": 1.0, "mid": 2.5, "far": 5.0}
BAND_TEXT = {"near": ", close.", "mid": ", a few steps.", "far": ", further ahead."}
KNOWN_RADIUS_M = 2.0
POSITION_RADIUS_M = 1.0
SCAN_POSITION_RADIUS_M = 1.5
WALK_ALIGN_M = 1.5
PICTURE_MAX_DIST_M = 3.0
SIDE_ANGLE = {"ahead": 0.0, "left": -25.0, "right": 25.0}
SIDES = {"ahead": ("ahead", "depth_centre"), "left": ("on your left", "depth_left"), "right": ("on your right", "depth_right")}


@dataclass(frozen=True)
class PolicyState:
    next_index: int = 0
    pause_sent: bool = False
    armed_at: Optional[float] = None
    first_frame_at: Optional[float] = None
    last_usable_at: Optional[float] = None
    last_frame_at: Optional[float] = None
    last_spoken_at: Optional[float] = None
    last_on_route_at: Optional[float] = None
    cued: Dict[str, Tuple[Optional[Tuple[float, float]], float]] = field(default_factory=dict)
    pending: Optional[tuple] = None


@dataclass(frozen=True)
class Cue:
    text: str
    priority: Optional[int]
    spoken: bool
    suppressed_reason: Optional[str]
    checkpoint: Optional[str] = None
    entity: Optional[str] = None
    route_version: Optional[int] = None
    trigger: Optional[str] = None
    would_have_said: Optional[str] = None
    details: Optional[dict] = None
    pre: Optional[list] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("pre")
        return d


def _latest(*ts):
    vals = [t for t in ts if t is not None]
    return max(vals) if vals else None


def _silent(reason: str, rv, text: str = "", priority=None, **kw) -> Cue:
    return Cue("", priority, False, reason, route_version=rv, would_have_said=text or None, **kw)


def _pause(state: PolicyState, rv, now: float, trigger: str):
    if state.pause_sent:
        return _silent("pause_already_sent", rv, PAUSE_TEXT, 0, trigger=trigger), state
    return Cue(PAUSE_TEXT, 0, True, None, route_version=rv, trigger=trigger), replace(state, pause_sent=True, last_spoken_at=now)


def _speak(state: PolicyState, cue: Cue, now: float, on_spoken, pending: Optional[tuple] = None):
    if cue.priority != 0 and state.last_spoken_at is not None and now - state.last_spoken_at < RATE_LIMIT_S:
        details = {**(cue.details or {}), "seconds_since_last": round(now - state.last_spoken_at, 2)}
        return replace(cue, text="", would_have_said=cue.text, spoken=False, suppressed_reason="rate_limited", details=details), replace(state, pending=pending)
    return cue, on_spoken(replace(state, last_spoken_at=now))


def _since_usable(state: PolicyState, now: float) -> float:
    base = _latest(state.last_usable_at, state.first_frame_at)
    return 0.0 if base is None else now - base


def _tick(state: PolicyState, rv, now: float):
    if state.pause_sent or state.armed_at is None:
        return None, state
    if state.first_frame_at is None:
        return _pause(state, rv, now, "no_frames") if now - state.armed_at >= GRACE_S else (None, state)
    if now - state.last_frame_at >= NO_FRAMES_S:
        return _pause(state, rv, now, "no_frames")
    if _since_usable(state, now) >= NO_USABLE_S:
        return _pause(state, rv, now, "no_usable_result")
    return None, state


def _label(raw: str) -> Tuple[str, str]:
    key = raw.strip().lower()
    return key, key[:1].upper() + key[1:]


def _distance(entity: dict, sensors: dict) -> Optional[float]:
    d = sensors.get(SIDES[entity["relation"]][1])
    return d if d is not None and d > 0 else None


def _entity_text(entity: dict, sensors: dict) -> str:
    words = SIDES[entity["relation"]][0]
    d = _distance(entity, sensors)
    if d is None:
        tail = BAND_TEXT[entity["distance_band"]]
    else:
        m = max(0.5, math.floor(d * 2 + 0.5) / 2)
        tail = f", about {m:g} {'metre' if m == 1 else 'metres'}."
    return f"{_label(entity['label'])[1]} {words}{tail}"


def alignment(trail_xz: list, scan: bool = False) -> Optional[tuple]:
    """The one run→route alignment (build_path, position rule, entity confirmation): run start → (0,0,0);
    on scan routes also rotate so the first WALK_ALIGN_M of walking faces −Z (None until walked)."""
    if not trail_xz:
        return None
    x0, z0 = trail_xz[0]
    if not scan:
        return (x0, z0, 1.0, 0.0)
    for x, z in trail_xz:
        if math.hypot(x - x0, z - z0) >= WALK_ALIGN_M:
            phi = -math.pi / 2 - math.atan2(z - z0, x - x0)
            return (x0, z0, math.cos(phi), math.sin(phi))
    return None


def to_route(align: tuple, x: float, z: float) -> tuple:
    ox, oz, c, s = align
    dx, dz = x - ox, z - oz
    return (c * dx - s * dz, s * dx + c * dz)


def run_align(sensors: dict) -> Optional[tuple]:
    if "align" in sensors:
        return sensors["align"]
    o = sensors.get("origin")
    return (o[0], o[1], 1.0, 0.0) if o else None


def entity_position(pos, align, heading, side: str, depth) -> Optional[list]:
    """Start-relative [x, z] of an object: client pos plus depth along heading (left -25°, right +25°), aligned to the route."""
    if pos is None or align is None or heading is None or depth is None:
        return None
    a = math.radians(heading + SIDE_ANGLE[side])
    x, z = to_route(align, pos[0] + math.sin(a) * depth, pos[1] - math.cos(a) * depth)
    return [round(x, 2), round(z, 2)]


def _known_match(key: str, position, segment: dict, known: list) -> Optional[dict]:
    for k in known:
        if isinstance(k, str):
            if k.strip().lower() == key:
                return {}
            continue
        if (k.get("label") or "").strip().lower() != key:
            continue
        kp = k.get("position")
        same = math.hypot(position[0] - kp[0], position[1] - kp[1]) <= KNOWN_RADIUS_M if position and kp else k.get("segment") == segment
        if same:
            return {"known_label": k.get("label"), "known_version": k.get("added_in")}
    return None


def _entity_info(entity: dict, state: PolicyState, sensors: dict, pos) -> dict:
    return {"confidence": entity["confidence"], "side": entity["relation"], "segment": {"from": state.next_index, "to": state.next_index + 1},
            "position": entity_position(pos, run_align(sensors), sensors.get("heading_deg"), entity["relation"], _distance(entity, sensors))}


def _entity_reason(entity: dict, state: PolicyState, known: list, no_repeat: bool, pos, now: float, sensors: dict) -> Tuple[Optional[str], dict]:
    key = _label(entity["label"])[0]
    details = _entity_info(entity, state, sensors, pos)
    if entity["confidence"] < MIN_CONFIDENCE:
        return "low_confidence", details
    hit = _known_match(key, details["position"], details["segment"], known)
    if hit is not None:
        return "known_entity", {**details, **hit}
    prev = state.cued.get(key) if no_repeat else None
    if prev:
        prev_pos, prev_t = prev
        details["seconds_since_last"] = round(now - prev_t, 2)
        if pos and prev_pos:
            details["metres_since_last"] = round(math.hypot(pos[0] - prev_pos[0], pos[1] - prev_pos[1]), 2)
            near = details["metres_since_last"] < DUP_RADIUS_M
        else:
            near = now - prev_t < DUP_WINDOW_S
        if near:
            return "duplicate", details
    return None, details


def _entities(state, entities, exercise, version, sensors, now, rv, pending=None):
    known = version.get("known_entities") or []
    no_repeat = bool((exercise.get("silence_rules") or {}).get("no_repeat", True))
    pos = (sensors["pos_x"], sensors["pos_z"]) if sensors.get("pos_x") is not None and sensors.get("pos_z") is not None else None
    ranked = sorted(entities, key=lambda e: (_distance(e, sensors) or BAND_M[e["distance_band"]], -e["confidence"]))
    if pending and pending[0] == "entity":
        ranked.sort(key=lambda e: (_label(e["label"])[0], e["relation"]) != pending[1:])
    reasons = [_entity_reason(e, state, known, no_repeat, pos, now, sensors) for e in ranked]
    for e, (reason, details) in zip(ranked, reasons):
        if reason is None:
            key, label = _label(e["label"])
            if pending and pending[0] == "entity" and (key, e["relation"]) == pending[1:]:
                details = {**details, "retry": True}
            cue = Cue(_entity_text(e, sensors), 1, True, None, entity=label, route_version=rv, details=details)
            return _speak(state, cue, now, lambda s: replace(s, cued={**s.cued, key: (pos, now)}), pending=("entity", key, e["relation"]))
    e = ranked[0]
    return _silent(reasons[0][0], rv, _entity_text(e, sensors), 1, entity=_label(e["label"])[1], details=reasons[0][1]), state


def pre_cues(cue: Cue) -> list:
    """Silent lines logged before a cue: a too-far picture match and/or the checkpoint passed over by a skip."""
    d = cue.details or {}
    return list(cue.pre or []) + ([skipped_cue(cue)] if d.get("skipped") and not d.get("retry") else [])


def skipped_cue(cue: Cue) -> Cue:
    """The silent log line for the checkpoint passed over when next+1 matched."""
    d = cue.details
    return _silent("checkpoint_skipped", cue.route_version, checkpoint=d["skipped"]["name"], details={"skipped": d["skipped"], "matched": d["matched"]})


def _position_hit(idx: int, sensors: dict) -> Optional[float]:
    """Distance to the next checkpoint when the fresh pose (run start = route start) is within POSITION_RADIUS_M; None if off/far."""
    cpp, al = (sensors.get("cp_positions") or {}).get(idx), run_align(sensors)
    if cpp is None or al is None or sensors.get("pos_x") is None or sensors.get("pos_z") is None:
        return None
    x, z = to_route(al, sensors["pos_x"], sensors["pos_z"])
    d = math.hypot(x - cpp[0], z - cpp[1])
    return round(d, 2) if d <= (SCAN_POSITION_RADIUS_M if sensors.get("scan") else POSITION_RADIUS_M) else None


def _picture_dist(idx: int, sensors: dict) -> Optional[float]:
    """Distance from the fresh, aligned pose to checkpoint idx; None (guard off) without a position, pose or alignment."""
    cpp, al = (sensors.get("cp_positions") or {}).get(idx), run_align(sensors)
    if cpp is None or al is None or sensors.get("pos_x") is None or sensors.get("pos_z") is None:
        return None
    x, z = to_route(al, sensors["pos_x"], sensors["pos_z"])
    return math.hypot(x - cpp[0], z - cpp[1])


def _checkpoint(state, idx, cps, exercise, rv, now, details, pending_by):
    cp = cps[idx]
    text = f"Checkpoint {idx + 1}: {cp['name']}."
    landmark = (cp.get("landmark_text") or "").strip()
    if exercise.get("cue_style") == "standard" and landmark:
        text = f"{text} {landmark}"
    cue = Cue(text, 2, True, None, checkpoint=cp["name"], route_version=rv, details=details)
    return _speak(state, cue, now, lambda s: replace(s, next_index=idx + 1), pending=("checkpoint", idx, pending_by))


def _usable(state, result, exercise, version, sensors, now, rv):
    cps = sorted(version.get("checkpoints") or [], key=lambda c: c["order"])
    match, idx, too_far = result.get("checkpoint_match"), state.next_index, None
    hit = next((i for i in (idx, idx + 1) if i < len(cps) and match == cps[i]["name"]), None)
    d = _picture_dist(hit, sensors) if hit is not None else None
    if d is not None and d > PICTURE_MAX_DIST_M:
        too_far = _silent("picture_too_far", rv, details={"checkpoint": {"order": cps[hit]["order"], "name": match}, "distance_m": round(d, 2), "max_m": PICTURE_MAX_DIST_M})
        match = None
    cue, state = _usable_match(state, result, match, cps, exercise, version, sensors, now, rv)
    if too_far is None:
        return cue, state
    if not cue.spoken and cue.suppressed_reason in ("on_route_silent", "nothing_to_say"):
        return too_far, state
    return replace(cue, pre=[too_far]), state


def _usable_match(state, result, match, cps, exercise, version, sensors, now, rv):
    pending, state = state.pending, replace(state, pause_sent=False, last_usable_at=now, pending=None)
    idx = state.next_index
    by = None
    if idx < len(cps):
        dist = _position_hit(idx, sensors)
        by = {"by": "picture"} if match == cps[idx]["name"] else {"by": "position", "distance_m": dist} if dist is not None else None
    retry = by is None and pending is not None and pending[0] == "checkpoint" and pending[1] == idx and idx < len(cps)
    if by or retry:
        by = by or (pending[2] if len(pending) > 2 and pending[2] else {"by": "picture"})
        return _checkpoint(state, idx, cps, exercise, rv, now, {**by, "retry": True} if retry else by, by)
    if match is not None and idx + 1 < len(cps) and match == cps[idx + 1]["name"]:
        skipped, hit = cps[idx], cps[idx + 1]
        details = {"by": "picture", "skipped": {"order": skipped["order"], "name": skipped["name"]}, "matched": {"order": hit["order"], "name": hit["name"]}}
        return _checkpoint(replace(state, next_index=idx + 1), idx + 1, cps, exercise, rv, now, details, {"by": "picture"})
    if result.get("new_entities"):
        return _entities(state, result["new_entities"], exercise, version, sensors, now, rv, pending)
    if (exercise.get("silence_rules") or {}).get("stay_silent_on_route", True):
        return _silent("on_route_silent", rv), state
    if result.get("on_route") and (state.last_on_route_at is None or now - state.last_on_route_at >= ON_ROUTE_EVERY_S):
        if state.last_spoken_at is not None and now - state.last_spoken_at < RATE_LIMIT_S:
            return _silent("nothing_to_say", rv, details={"talking_over": True}), state
        return Cue(ON_ROUTE_TEXT, 2, True, None, route_version=rv), replace(state, last_on_route_at=now)
    return _silent("nothing_to_say", rv), state


def decide(state: PolicyState, event: dict, exercise: dict, version: dict, sensors: dict, now: float):
    """event type: running | tick | vision | vision_error | vision_stopped. Returns (Cue or None, new state)."""
    rv = version.get("version")
    state = replace(state, last_frame_at=_latest(state.last_frame_at, sensors.get("last_frame_at")))
    if state.armed_at is not None and state.first_frame_at is None and state.last_frame_at is not None and state.last_frame_at > state.armed_at:
        state = replace(state, first_frame_at=state.last_frame_at)
    kind = event["type"]
    if kind == "running":
        return None, replace(state, armed_at=now, first_frame_at=None)
    if kind == "tick":
        return _tick(state, rv, now)
    if kind == "vision_stopped":
        return _pause(state, rv, now, "vision_stopped")
    if kind == "vision_error":
        if _since_usable(state, now) >= NO_USABLE_S:
            return _pause(state, rv, now, "no_usable_result")
        return _silent("vision_error", rv, details={"error": event.get("reason")}), state
    result = event.get("result") or {}
    if result.get("unusable"):
        if _since_usable(state, now) >= NO_USABLE_S:
            return _pause(state, rv, now, "no_usable_result")
        return _silent("unusable_frame", rv), state
    return _usable(state, result, exercise, version, sensors, now, rv)
