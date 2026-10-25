"""Read-only machine view of confirmed route memory: one serializer shared by the review, history and memory endpoint."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from db import db

router = APIRouter(prefix="/api")

SOURCE = "BetweenVisit route memory"
ADVICE = {
    "right": "Reported {label} right of the path; keep left.",
    "ahead": "Reported {label} ahead on the path; keep left.",
    "left": "Reported {label} left of the path; keep right.",
}


def position_out(x, y, z) -> dict:
    r = lambda v: None if v is None else round(v, 3)
    return {"x": r(x), "y": r(y), "z": r(z), "units": "m", "origin": "route_start"}


def machine_entity(route_id: str, version: int, e: dict) -> dict:
    side = e.get("side") or "ahead"
    pos = e.get("position")
    return {
        "type": "REPLAN_RIGHT" if side == "left" else "REPLAN_LEFT",
        "authoritative": False,
        "source": SOURCE,
        "route_id": route_id,
        "version": version,
        "entity": {
            "label": e["label"], "side": side, "segment": e.get("segment"),
            "position": position_out(pos[0], None, pos[1]) if pos else None,
            "verified_by": e.get("verified_by"), "verified_at": e.get("verified_at"),
        },
        "advice": ADVICE[side].format(label=e["label"]),
    }


async def checkpoint_positions(version: dict) -> dict:
    """Start-relative positions for taught routes (teach position minus teach start); empty for routes without 3D memory."""
    from review import load_memory
    loaded = await load_memory(version["memory_id"]) if version.get("memory_id") else None
    trail = (loaded[1].get("trail") or []) if loaded else []
    if not trail:
        return {}
    s = trail[0]
    ids = [c["id"] for c in version.get("checkpoints", [])]
    stored = {c["id"]: c.get("position") for c in await db.checkpoints.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "position": 1}).to_list(100)}
    out = {}
    for c in version.get("checkpoints", []):
        p = c.get("position") or stored.get(c["id"])
        if p:
            out[c["id"]] = position_out(p[0] - s[0], p[1] - s[1], p[2] - s[2])
    return out


@router.get("/routes/{route_id}/memory")
async def route_memory(route_id: str, version: Optional[int] = None):
    route = await db.routes.find_one({"id": route_id}, {"_id": 0, "is_test": 1})
    if not route or route.get("is_test"):
        raise HTTPException(status_code=404, detail="Route not found")
    q = {"route_id": route_id, **({"version": version} if version is not None else {})}
    v = await db.route_versions.find_one(q, {"_id": 0}, sort=[("version", -1)])
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    pos = await checkpoint_positions(v)
    return {
        "source": SOURCE, "authoritative": False, "route_id": route_id, "version": v["version"],
        "checkpoints": [{"order": c["order"], "name": c["name"], "landmark_text": c["landmark_text"], "position": pos.get(c["id"])}
                        for c in sorted(v.get("checkpoints", []), key=lambda c: c["order"])],
        "entities": [machine_entity(route_id, v["version"], e) for e in v.get("known_entities") or [] if isinstance(e, dict)],
    }
