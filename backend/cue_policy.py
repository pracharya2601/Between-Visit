"""Relevance policy: pure, deterministic rules that turn one input into at most one cue. No I/O, no clock."""
import math
from dataclasses import asdict, dataclass, field, replace
from typing import Dict, Optional, Tuple

PAUSE_TEXT = "Vision unavailable, please pause."
ON_ROUTE_TEXT = "On route."
NO_FRAMES_S = 2.0
NO_USABLE_S = 5.0
ON_ROUTE_EVERY_S = 20.0
RATE_LIMIT_S = 3.0
DUP_RADIUS_M = 3.0
DUP_WINDOW_S = 20.0
MIN_CONFIDENCE = 0.6
BAND_M = {"near": 1.0, "mid": 2.5, "far": 5.0}
BAND_TEXT = {"near": ", close.", "mid": ", a few steps.", "far": ", further ahead."}
SIDES = {"ahead": ("ahead", "depth_centre"), "left": ("on your left", "depth_left"), "right": ("on your right", "depth_right")}


@dataclass(frozen=True)
class PolicyState:
    next_index: int = 0
    pause_sent: bool = False
    armed_at: Optional[float] = None
    last_usable_at: Optional[float] = None
    last_frame_at: Optional[float] = None
    last_spoken_at: Optional[float] = None
    last_on_route_at: Optional[float] = None
    cued: Dict[str, Tuple[Optional[Tuple[float, float]], float]] = field(default_factory=dict)


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

    def as_dict(self) -> dict:
        return asdict(self)


def _latest(*ts):
    vals = [t for t in ts if t is not None]
    return max(vals) if vals else None


def _silent(reason: str, rv, text: str = "", priority=None, **kw) -> Cue:
    return Cue(text, priority, False, reason, route_version=rv, **kw)


def _pause(state: PolicyState, rv, now: float, trigger: str):
    if state.pause_sent:
        return _silent("pause_already_sent", rv, PAUSE_TEXT, 0, trigger=trigger), state
    return Cue(PAUSE_TEXT, 0, True, None, route_version=rv, trigger=trigger), replace(state, pause_sent=True, last_spoken_at=now)


def _speak(state: PolicyState, cue: Cue, now: float, on_spoken):
    if cue.priority != 0 and state.last_spoken_at is not None and now - state.last_spoken_at < RATE_LIMIT_S:
        return replace(cue, spoken=False, suppressed_reason="rate_limited"), state
    return cue, on_spoken(replace(state, last_spoken_at=now))


def _since_usable(state: PolicyState, now: float) -> float:
    base = _latest(state.last_usable_at, state.armed_at)
    return 0.0 if base is None else now - base


def _tick(state: PolicyState, rv, now: float):
    if state.pause_sent or state.armed_at is None:
        return None, state
    if now - _latest(state.last_frame_at, state.armed_at) >= NO_FRAMES_S:
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


def _entity_reason(entity: dict, state: PolicyState, known: set, no_repeat: bool, pos, now: float) -> Optional[str]:
    key = _label(entity["label"])[0]
    if entity["confidence"] < MIN_CONFIDENCE:
        return "low_confidence"
    if key in known:
        return "known_entity"
    prev = state.cued.get(key) if no_repeat else None
    if prev:
        prev_pos, prev_t = prev
        near = math.hypot(pos[0] - prev_pos[0], pos[1] - prev_pos[1]) < DUP_RADIUS_M if pos and prev_pos else now - prev_t < DUP_WINDOW_S
        if near:
            return "duplicate"
    return None


def _entities(state, entities, exercise, version, sensors, now, rv):
    known = {(k.get("label", "") if isinstance(k, dict) else str(k)).strip().lower() for k in version.get("known_entities") or []}
    no_repeat = bool((exercise.get("silence_rules") or {}).get("no_repeat", True))
    pos = (sensors["pos_x"], sensors["pos_z"]) if sensors.get("pos_x") is not None and sensors.get("pos_z") is not None else None
    ranked = sorted(entities, key=lambda e: (_distance(e, sensors) or BAND_M[e["distance_band"]], -e["confidence"]))
    reasons = [_entity_reason(e, state, known, no_repeat, pos, now) for e in ranked]
    for e, reason in zip(ranked, reasons):
        if reason is None:
            key, label = _label(e["label"])
            cue = Cue(_entity_text(e, sensors), 1, True, None, entity=label, route_version=rv)
            return _speak(state, cue, now, lambda s: replace(s, cued={**s.cued, key: (pos, now)}))
    e = ranked[0]
    return _silent(reasons[0], rv, _entity_text(e, sensors), 1, entity=_label(e["label"])[1]), state


def _usable(state, result, exercise, version, sensors, now, rv):
    state = replace(state, pause_sent=False, last_usable_at=now)
    cps = sorted(version.get("checkpoints") or [], key=lambda c: c["order"])
    match = result.get("checkpoint_match")
    if match is not None and state.next_index < len(cps) and match == cps[state.next_index]["name"]:
        n, cp = state.next_index + 1, cps[state.next_index]
        text = f"Checkpoint {n}: {cp['name']}."
        landmark = (cp.get("landmark_text") or "").strip()
        if exercise.get("cue_style") == "standard" and landmark:
            text = f"{text} {landmark}"
        return _speak(state, Cue(text, 2, True, None, checkpoint=cp["name"], route_version=rv), now, lambda s: replace(s, next_index=n))
    if result.get("new_entities"):
        return _entities(state, result["new_entities"], exercise, version, sensors, now, rv)
    if (exercise.get("silence_rules") or {}).get("stay_silent_on_route", True):
        return _silent("on_route_silent", rv), state
    if result.get("on_route") and (state.last_on_route_at is None or now - state.last_on_route_at >= ON_ROUTE_EVERY_S):
        return _speak(state, Cue(ON_ROUTE_TEXT, 2, True, None, route_version=rv), now, lambda s: replace(s, last_on_route_at=now))
    return _silent("nothing_to_say", rv), state


def decide(state: PolicyState, event: dict, exercise: dict, version: dict, sensors: dict, now: float):
    """event type: running | tick | vision | vision_error | vision_stopped. Returns (Cue or None, new state)."""
    rv = version.get("version")
    state = replace(state, last_frame_at=_latest(state.last_frame_at, sensors.get("last_frame_at")))
    kind = event["type"]
    if kind == "running":
        return None, replace(state, armed_at=now)
    if kind == "tick":
        return _tick(state, rv, now)
    if kind == "vision_stopped":
        return _pause(state, rv, now, "vision_stopped")
    if kind == "vision_error":
        if _since_usable(state, now) >= NO_USABLE_S:
            return _pause(state, rv, now, "no_usable_result")
        return _silent("vision_error", rv), state
    result = event.get("result") or {}
    if result.get("unusable"):
        return _pause(state, rv, now, "unusable")
    return _usable(state, result, exercise, version, sensors, now, rv)
