"""Practitioner-only attempt review: header stats, readable timeline and path data in one response."""
import json
import math
from datetime import datetime
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Response

from corrections import correction_out, entity_facts
from db import db
from machine import machine_entity
from models import Attempt
from storage import get_object

router = APIRouter(prefix="/api")

ROUTINE = {"on_route_silent", "nothing_to_say"}
STEP_M = 0.7
BROWSER_POINTS = 50_000
RUN_TEXT = {"start": "Run started", "pause": "Paused", "resume": "Resumed", "end": "Ended"}
FIXED_REASONS = {"known_entity": "Already part of the route", "pause_already_sent": "Pause message already given", "vision_error": "Vision check failed"}
MEMORY_CACHE: dict = {}


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp()


def _n(v: float) -> str:
    return f"{round(v, 1):g}"


def plain_reason(reason: str, d: Optional[dict]) -> str:
    d = d or {}
    if reason == "duplicate":
        if d.get("metres_since_last") is not None:
            return f"Not repeated: already said {_n(d['metres_since_last'])} m ago"
        return f"Not repeated: already said {_n(d.get('seconds_since_last', 0))} s ago"
    if reason == "rate_limited":
        return f"Held back: another cue {math.floor(d.get('seconds_since_last', 0) * 10) / 10:g} s earlier"
    if reason == "low_confidence":
        return f"Not sure enough (confidence {d.get('confidence', 0):.2f})"
    if reason == "known_entity" and d.get("known_version"):
        return f"Known: {d.get('known_label')} confirmed in v{d['known_version']}"
    return FIXED_REASONS.get(reason, reason)


def dead_reckoning(motion: list) -> list:
    """Top-down points from heading + step samples: ~0.7 m per step, +X east, -Z north."""
    pts, x, z, prev = [], 0.0, 0.0, None
    for m in motion:
        if prev is not None:
            d = max(0, m["steps"] - prev) * STEP_M
            h = math.radians(m["heading"])
            x, z = x + math.sin(h) * d, z - math.cos(h) * d
        prev = m["steps"]
        pts.append({"x": round(x, 3), "z": round(z, 3), "t": _ts(m["t"])})
    return pts


def _raw(e: Optional[dict]) -> Optional[dict]:
    if not e:
        return None
    keep = ("type", "t", "result", "reason", "model", "latency_ms", "route_version", "source", "checkpoint", "uncertain",
            "pos_x", "pos_z", "heading_deg", "ar_tracking", "depth_left", "depth_centre", "depth_right")
    return {k: e.get(k) for k in keep if e.get(k) is not None}


def _item(e: dict, t0: float, **kw) -> dict:
    return {"id": e["id"], "seq": e["seq"], "at": max(0.0, round(_ts(e["t"]) - t0, 1)), "text": "", "reason": None, "category": "event", "pos": None, "raw": None,
            "would_have_said": False, "entity": None, "correction": None, "machine": None, **kw}


def cue_item(e: dict, t0: float, vision: dict, ctx: dict) -> dict:
    pos = [e["pos_x"], e["pos_z"]] if e.get("pos_x") is not None and e.get("pos_z") is not None else None
    v = vision.get(e.get("for_event_id"))
    raw = {"vision": _raw(v), "policy": {k: e.get(k) for k in ("reason", "suppressed_reason", "priority", "details", "entity", "checkpoint")}}
    extra = {}
    if e.get("entity"):
        f = entity_facts(e, v, ctx["trail"], ctx["reached"])
        c = ctx["corrections"].get(e["id"])
        extra = {"entity": {"label": f["label"], "side": f["side"]}, "correction": correction_out(c) if c else None}
    if e["spoken"]:
        kind, label = ("checkpoint", "Checkpoint reached") if e.get("checkpoint") else ("unavailable", "Vision unavailable") if e.get("priority") == 0 else ("cue", "Spoken cue")
        return _item(e, t0, kind=kind, label=label, text=e["text"], category="spoken", pos=pos, raw=raw, **extra)
    if e["suppressed_reason"] == "vision_error":
        return _item(e, t0, kind="suppressed", label="Not spoken", text="Vision check failed (stayed silent)", category="suppressed", pos=pos, raw=raw)
    said = e.get("would_have_said")
    return _item(e, t0, kind="suppressed", label="Not spoken", text=said or "Stayed silent", would_have_said=bool(said),
                 reason=plain_reason(e["suppressed_reason"], e.get("details")), category="suppressed", pos=pos, raw=raw, **extra)


def build_timeline(events: list, t0: float, trail: Optional[list] = None, corrections: Optional[dict] = None):
    vision = {e["id"]: e for e in events if e["type"] in ("vision", "vision_error")}
    items, routine = [], 0
    reached: set = set()
    ctx = {"trail": trail or [], "corrections": corrections or {}, "reached": 0}
    for e in events:
        ty = e["type"]
        ctx["reached"] = len(reached)
        if ty == "cue" and e["spoken"] and e.get("checkpoint"):
            reached.add(e["checkpoint"])
        if ty in RUN_TEXT:
            items.append(_item(e, t0, kind="run", label="Run", text=RUN_TEXT[ty]))
        elif ty == "help":
            items.append(_item(e, t0, kind="help", label="Help", text="Help requested"))
        elif ty == "guide" and e.get("reason") != "policy":
            items.append(_item(e, t0, kind="message", label="Practitioner message", text=e["text"]))
        elif ty == "repeat":
            items.append(_item(e, t0, kind="repeat", label="Repeat", text=f"Client asked to repeat: {e['text']}"))
        elif ty == "vision" and e.get("uncertain"):
            items.append(_item(e, t0, kind="uncertain", label="Vision unsure", text="Vision wasn't sure what it saw", raw={"vision": _raw(e)}))
        elif ty == "vision_stopped":
            items.append(_item(e, t0, kind="vision_stopped", label="Vision stopped", text="Vision stopped at the 30-minute limit"))
        elif ty == "cue":
            if not e["spoken"] and e.get("suppressed_reason") in ROUTINE:
                routine += 1
            else:
                items.append(cue_item(e, t0, vision, ctx))
    return items, routine


async def load_memory(memory_id: str):
    if memory_id not in MEMORY_CACHE:
        mem = await db.route_memories.find_one({"id": memory_id}, {"_id": 0})
        if not mem:
            return None
        MEMORY_CACHE[memory_id] = (mem, json.loads(await get_object(mem["json_path"])))
    return MEMORY_CACHE[memory_id]


def place(entities: list, ox: float, oz: float) -> list:
    """Known-entity markers: start-relative positions moved onto the view's start point; no position -> listed, not drawn."""
    return [{**{k: e.get(k) for k in ("id", "label", "side", "added_in", "segment", "position", "machine")},
             "pos": [round(e["position"][0] + ox, 3), round(e["position"][1] + oz, 3)] if e.get("position") else None} for e in entities]


async def known_for_review(version: dict, corrections: dict, route_id: str) -> list:
    """The attempt version's known entities plus any confirmed from this attempt into later versions."""
    out = {e["id"]: {**e, "machine": machine_entity(route_id, version["version"], e)} for e in version.get("known_entities") or [] if isinstance(e, dict) and e.get("id")}
    for c in corrections.values():
        if c.get("new_route_version"):
            v = await db.route_versions.find_one({"route_id": route_id, "version": c["new_route_version"]}, {"_id": 0, "known_entities": 1}) or {}
            for e in v.get("known_entities") or []:
                if isinstance(e, dict) and e.get("from_event_id") == c["attempt_event_id"]:
                    out.setdefault(e["id"], {**e, "machine": machine_entity(route_id, c["new_route_version"], e)})
    return list(out.values())


async def build_path(doc: dict, version: dict, items: list, entities: Optional[list] = None) -> dict:
    entities = entities or []
    run_trail = [(p["x"], p["z"]) for p in doc.get("trail") or []]
    dots = [i for i in items if i["category"] != "event"]
    loaded = await load_memory(version["memory_id"]) if version.get("memory_id") else None
    if loaded:
        mem, meta = loaded
        teach = meta.get("trail") or []
        y = teach[0][1] if teach else 0.0
        aligned = bool(run_trail and teach)
        ox, oz = (teach[0][0] - run_trail[0][0], teach[0][2] - run_trail[0][1]) if aligned else (0.0, 0.0)
        for i in dots:
            if i["pos"]:
                i["pos"] = [round(i["pos"][0] + ox, 3), round(i["pos"][1] + oz, 3)]
        ids = [c["id"] for c in version.get("checkpoints", [])]
        pos = {c["id"]: c.get("position") for c in await db.checkpoints.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "position": 1}).to_list(100)}
        scene = {
            "points": mem["point_count"], "points_sent": min(mem["point_count"], BROWSER_POINTS), "planes": meta.get("planes", []),
            "trail": [p[:3] for p in teach], "metres_walked": mem["trail_m"],
            "checkpoints": [{"id": c["id"], "order": c["order"], "name": c["name"], "position": pos.get(c["id"])} for c in version.get("checkpoints", [])],
        }
        t0 = (teach[0][0], teach[0][2]) if teach else (0.0, 0.0)
        return {"mode": "3d", "aligned": aligned, "floor_y": y, "run_trail": [[x + ox, y, z + oz] for x, z in run_trail], "scene": scene, "entities": place(entities, *t0)}
    if run_trail:
        return {"mode": "2d", "source": "trail", "trail": [list(p) for p in run_trail], "entities": place(entities, *run_trail[0])}
    motion = doc.get("motion") or []
    if motion:
        dr = dead_reckoning(motion)
        for i in dots:
            if not i["pos"]:
                t = i["at"] + _ts(doc["started_at"])
                p = next((q for q in reversed(dr) if q["t"] <= t), dr[0])
                i["pos"] = [p["x"], p["z"]]
        return {"mode": "2d", "source": "steps", "trail": [[p["x"], p["z"]] for p in dr], "entities": place(entities, 0.0, 0.0)}
    for i in dots:
        i["pos"] = None
    return {"mode": "none", "entities": place(entities, 0.0, 0.0)}


async def _attempt(attempt_id: str):
    doc = await db.attempts.find_one({"id": attempt_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Attempt not found")
    a = Attempt.from_mongo(doc)
    if a.status == "not_started" or not a.started_at:
        raise HTTPException(status_code=409, detail="This attempt hasn't started yet.")
    ex = await db.exercises.find_one({"id": a.exercise_id}, {"_id": 0}) or {}
    version = await db.route_versions.find_one({"route_id": ex.get("route_id"), "version": a.route_version}, {"_id": 0}) or {}
    return doc, a, ex, version


@router.get("/attempts/{attempt_id}/review")
async def attempt_review(attempt_id: str):
    doc, a, ex, version = await _attempt(attempt_id)
    client = await db.clients.find_one({"id": ex.get("client_id")}, {"_id": 0, "display_name": 1}) or {}
    route = await db.routes.find_one({"id": ex.get("route_id")}, {"_id": 0, "name": 1}) or {}
    events = await db.attempt_events.find({"attempt_id": a.id}, {"_id": 0}).sort("seq", 1).to_list(5000)
    ids = [e["id"] for e in events if e["type"] == "cue" and e.get("entity")]
    corrections = {c["attempt_event_id"]: c for c in await db.corrections.find({"attempt_event_id": {"$in": ids}}, {"_id": 0}).to_list(1000)}
    items, routine = build_timeline(events, _ts(a.started_at), doc.get("trail") or [], corrections)
    cues = [e for e in events if e["type"] == "cue"]
    header = {
        "client": client.get("display_name", ""), "route": route.get("name", ""), "version": a.route_version, "route_id": ex.get("route_id"), "goal": ex.get("goal", ""),
        "status": a.status, "stream_id": a.stream_id, "started_at": a.started_at, "ended_at": a.ended_at, "elapsed_seconds": a.elapsed_seconds(),
        "checkpoints_reached": len({e["checkpoint"] for e in cues if e["spoken"] and e.get("checkpoint")}),
        "checkpoints_total": len(version.get("checkpoints", [])),
        "help_count": sum(e["type"] == "help" for e in events),
        "cues_spoken": sum(e["spoken"] for e in cues),
        "cues_suppressed": sum(not e["spoken"] and e.get("suppressed_reason") not in ROUTINE for e in cues),
        "routine_hidden": routine,
    }
    entities = await known_for_review(version, corrections, ex.get("route_id"))
    by_event = {e.get("from_event_id"): e["machine"] for e in entities if e.get("from_event_id")}
    for i in items:
        if i["correction"] and i["correction"].get("new_route_version"):
            i["machine"] = by_event.get(i["id"])
    return {"header": header, "timeline": items, "path": await build_path(doc, version, items, entities)}


@router.get("/attempts/{attempt_id}/review/points")
async def attempt_review_points(attempt_id: str):
    _, _, _, version = await _attempt(attempt_id)
    mem = await db.route_memories.find_one({"id": version.get("memory_id")}, {"_id": 0}) if version.get("memory_id") else None
    if not mem:
        raise HTTPException(status_code=404, detail="No 3D memory for this route version")
    pts = np.frombuffer(await get_object(mem["points_path"]), dtype="<f4").reshape(-1, 3)
    if len(pts) > BROWSER_POINTS:
        pts = pts[np.linspace(0, len(pts) - 1, BROWSER_POINTS).astype(np.int64)]
    return Response(content=pts.tobytes(), media_type="application/octet-stream", headers={"X-Point-Count": str(len(pts))})
