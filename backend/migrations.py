import logging
import json
import re

from db import db
from models import now_iso
from storage import delete_object

logger = logging.getLogger(__name__)

CHECK_ROUTES = ["Check route (synthetic)", "Library entrance (synthetic)"]
PHASE4_DEMO_ROUTES = ["Reception route (synthetic)", "Unsaved draft (synthetic)"]
TEST_ROUTE = "Test route (synthetic)"


async def delete_routes_cascade(route_ids: list) -> dict:
    """Deletes routes with checkpoints, versions, exercises, attempts and events; photos become unservable."""
    cp_ids = await db.checkpoints.distinct("id", {"route_id": {"$in": route_ids}})
    photos = await db.photos.find({"$or": [{"checkpoint_id": {"$in": cp_ids}}, {"route_id": {"$in": route_ids}}], "is_deleted": {"$ne": True}}, {"_id": 0, "id": 1, "storage_path": 1}).to_list(10000)
    deleted_in_storage = 0
    for p in photos:
        ok = await delete_object(p["storage_path"])
        deleted_in_storage += ok
        await db.photos.update_one({"id": p["id"]}, {"$set": {"is_deleted": True, "storage_deleted": ok}})
    ex_ids = await db.exercises.distinct("id", {"route_id": {"$in": route_ids}})
    att_ids = await db.attempts.distinct("id", {"exercise_id": {"$in": ex_ids}})
    return {
        "routes": (await db.routes.delete_many({"id": {"$in": route_ids}})).deleted_count,
        "checkpoints": (await db.checkpoints.delete_many({"id": {"$in": cp_ids}})).deleted_count,
        "route_versions": (await db.route_versions.delete_many({"route_id": {"$in": route_ids}})).deleted_count,
        "exercises": (await db.exercises.delete_many({"id": {"$in": ex_ids}})).deleted_count,
        "attempts": (await db.attempts.delete_many({"id": {"$in": att_ids}})).deleted_count,
        "attempt_events": (await db.attempt_events.delete_many({"attempt_id": {"$in": att_ids}})).deleted_count,
        "photos_unservable": [p["id"] for p in photos],
        "photos_deleted_in_storage": deleted_in_storage,
    }


async def cleanup_once(marker: str, names: list):
    if await db.migrations.find_one({"id": marker}):
        return
    route_ids = await db.routes.distinct("id", {"name": {"$in": names}, "is_test": {"$ne": True}})
    result = await delete_routes_cascade(route_ids)
    await db.migrations.insert_one({"id": marker, "created_at": now_iso(), "result": result})
    logger.info("%s: %s", marker, result)


async def phase4_cleanup():
    await cleanup_once("phase4-cleanup", CHECK_ROUTES)


async def phase5_cleanup():
    await cleanup_once("phase5-cleanup", PHASE4_DEMO_ROUTES)


PHASE6_ROUTE_IDS = ["b970d705-4f36-43ed-9163-d2e42bf5ea2e", "a5ffedc8-237a-473e-92dd-4642d82fa68e"]


async def phase6_cleanup():
    if await db.migrations.find_one({"id": "phase6-cleanup"}):
        return
    result = await delete_routes_cascade(PHASE6_ROUTE_IDS)
    test_routes = await db.routes.distinct("id", {"is_test": True})
    empty = {"route_id": {"$in": test_routes}, "name": "", "photo_url": None}
    result["test_route_empty_checkpoints"] = (await db.checkpoints.delete_many(empty)).deleted_count
    await db.migrations.insert_one({"id": "phase6-cleanup", "created_at": now_iso(), "result": result})
    logger.info("phase6-cleanup: %s", result)


async def phase11_attempt_versions():
    """Copies each exercise's pinned version onto its attempts that don't have their own yet."""
    for a in await db.attempts.find({"route_version": {"$exists": False}}, {"_id": 0, "id": 1, "exercise_id": 1}).to_list(10000):
        ex = await db.exercises.find_one({"id": a["exercise_id"]}, {"_id": 0, "route_version": 1}) or {}
        await db.attempts.update_one({"id": a["id"]}, {"$set": {"route_version": ex.get("route_version", 0)}})


async def phase4_model_updates():
    await db.routes.update_many({"name": TEST_ROUTE, "is_test": {"$ne": True}}, {"$set": {"is_test": True}})
    await db.exercises.update_many(
        {"silence_rules": {"$type": "string"}},
        {"$set": {"silence_rules": {"stay_silent_on_route": True, "no_repeat": True, "note": None}}},
    )
    await db.exercises.update_many({"route_version": {"$exists": False}}, {"$set": {"route_version": 0}})


DEMO_3D_OLD, DEMO_3D_NEW = "Review demo route 3D (synthetic)", "Entrance → hallway turn → reception desk (synthetic)"
DEMO_2D_OLD, DEMO_2D_NEW = "Review demo route 2D (synthetic)", "Lobby to elevator (synthetic)"
CP_RENAMES = {"Start": "Entrance", "Turn 1": "Hallway turn", "End": "Reception desk"}
CP_PREFIX = re.compile(r"^(Checkpoint \d+: )(Start|Turn 1|End)\b")


def _rename(o):
    """Renames old checkpoint names in exact-match strings and 'Checkpoint N: <name>' texts, recursively."""
    if isinstance(o, dict):
        return {k: _rename(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_rename(v) for v in o]
    if isinstance(o, str):
        return CP_RENAMES.get(o) or CP_PREFIX.sub(lambda m: m.group(1) + CP_RENAMES[m.group(2)], o)
    return o


async def _rewrite(coll: str, query: dict) -> int:
    n = 0
    async for d in db[coll].find(query):
        new = _rename({k: v for k, v in d.items() if k not in ("_id", "id")})
        if any(new[k] != d[k] for k in new):
            await db[coll].update_one({"_id": d["_id"]}, {"$set": new})
            n += 1
    return n


async def phase14_demo_renames():
    """One-off, user-approved rename of the two synthetic demo routes (exception to 'history never rewritten')."""
    marker = "phase14-demo-renames"
    if await db.migrations.find_one({"id": marker}):
        return
    result = {}
    r3 = await db.routes.find_one({"name": {"$in": [DEMO_3D_OLD, DEMO_3D_NEW]}}, {"_id": 0, "id": 1})
    if r3:
        rid = r3["id"]
        await db.routes.update_one({"id": rid}, {"$set": {"name": DEMO_3D_NEW}})
        exs = [e["id"] for e in await db.exercises.find({"route_id": rid}, {"_id": 0, "id": 1}).to_list(1000)]
        atts = [a["id"] for a in await db.attempts.find({"exercise_id": {"$in": exs}}, {"_id": 0, "id": 1}).to_list(10000)]
        for coll, q in (("checkpoints", {"route_id": rid}), ("route_versions", {"route_id": rid}), ("recordings", {"route_id": rid}),
                        ("attempt_events", {"attempt_id": {"$in": atts}}), ("progress_notes", {"attempt_id": {"$in": atts}})):
            result[coll] = await _rewrite(coll, q)
        result["route_3d"] = rid
    r2 = await db.routes.update_one({"name": DEMO_2D_OLD}, {"$set": {"name": DEMO_2D_NEW}})
    result["route_2d_renamed"] = r2.modified_count
    await db.migrations.insert_one({"id": marker, "created_at": now_iso(), "result": result})
    logger.info("%s: %s", marker, result)


DEMO_CHAIR = (0.6, -5.0)


def synthetic_corridor(seed: int = 15):
    """~40k coloured points + planes for the demo corridor: +Y up, -Z north, +X east, start-relative."""
    import numpy as np
    rng = np.random.default_rng(seed)
    parts = []

    def box(n, x, y, z, rgb, jitter=10):
        p = np.column_stack([rng.uniform(*x, n), rng.uniform(*y, n), rng.uniform(*z, n)])
        c = np.clip(np.array(rgb) + rng.integers(-jitter, jitter + 1, (n, 3)), 0, 255)
        parts.append((p, c))

    floor, wall, rail = (178, 170, 156), (232, 228, 218), (168, 172, 178)
    box(7000, (-0.9, 0.9), (0, 0), (-10.9, 0.5), floor)
    box(7000, (-0.9, 7.2), (0, 0), (-10.9, -9.1), floor)
    box(1400, (-0.15, 0.15), (0.002, 0.002), (-10.0, 0.5), (226, 186, 30), 8)
    box(1100, (-0.15, 6.4), (0.002, 0.002), (-10.15, -9.85), (226, 186, 30), 8)
    box(5000, (-0.9, -0.9), (0, 2.6), (-10.9, 0.5), wall)
    box(4200, (0.9, 0.9), (0, 2.6), (-9.1, 0.5), wall)
    box(3800, (-0.9, 7.2), (0, 2.6), (-10.9, -10.9), wall)
    box(2900, (0.9, 7.2), (0, 2.6), (-9.1, -9.1), wall)
    box(900, (7.2, 7.2), (0, 2.6), (-10.9, -9.1), wall)
    box(900, (-0.85, -0.82), (0.88, 0.92), (-10.85, 0.5), rail, 20)
    box(700, (-0.85, 7.2), (0.88, 0.92), (-10.85, -10.82), rail, 20)
    box(1300, (6.4, 7.1), (1.0, 1.0), (-10.7, -9.3), (150, 101, 52))
    box(1200, (6.4, 6.4), (0, 1.0), (-10.7, -9.3), (128, 84, 42))
    cx, cz = DEMO_CHAIR
    box(500, (cx - 0.22, cx + 0.22), (0.45, 0.47), (cz - 0.22, cz + 0.22), (32, 32, 34), 6)
    box(400, (cx + 0.2, cx + 0.22), (0.45, 0.9), (cz - 0.22, cz + 0.22), (32, 32, 34), 6)
    for dx in (-0.2, 0.2):
        for dz in (-0.2, 0.2):
            box(60, (cx + dx - 0.015, cx + dx + 0.015), (0, 0.45), (cz + dz - 0.015, cz + dz + 0.015), (40, 40, 44), 6)
    pts = np.concatenate([p for p, _ in parts]) + rng.normal(0, 0.012, (sum(len(p) for p, _ in parts), 3))
    cols = np.concatenate([c for _, c in parts]).astype(np.uint8)
    half = 3.14159265 / 2
    planes = [
        {"id": "floorN", "class": "floor", "align": "horizontal", "center": [0, 0, -5.2], "extent": [1.8, 11.4], "rotation_y": 0},
        {"id": "floorE", "class": "floor", "align": "horizontal", "center": [3.15, 0, -10], "extent": [8.1, 1.8], "rotation_y": 0},
        {"id": "wallW", "class": "wall", "align": "vertical", "center": [-0.9, 1.3, -5.2], "extent": [11.4, 2.6], "rotation_y": half},
        {"id": "wallE", "class": "wall", "align": "vertical", "center": [0.9, 1.3, -4.3], "extent": [9.6, 2.6], "rotation_y": half},
        {"id": "wallN", "class": "wall", "align": "vertical", "center": [3.15, 1.3, -10.9], "extent": [8.1, 2.6], "rotation_y": 0},
        {"id": "wallS", "class": "wall", "align": "vertical", "center": [4.05, 1.3, -9.1], "extent": [6.3, 2.6], "rotation_y": 0},
        {"id": "wallEnd", "class": "wall", "align": "vertical", "center": [7.2, 1.3, -10], "extent": [1.8, 2.6], "rotation_y": half},
    ]
    trail = [[0.0, 0.0, round(-0.25 * i, 2)] for i in range(41)] + [[round(0.25 * i, 2), 0.0, -10.0] for i in range(1, 25)]
    return pts.astype("<f4"), cols, planes, trail


async def phase15_synthetic_model():
    """One-off, user-approved: synthetic 3D memory for the 3D demo route (v1 + v2), v2 chair position, recording depth tweak."""
    from models import RouteMemory
    from storage import put_object
    marker = "phase15-synthetic-model"
    if await db.migrations.find_one({"id": marker}):
        return
    route = await db.routes.find_one({"name": DEMO_3D_NEW}, {"_id": 0, "id": 1})
    if not route:
        return
    rid = route["id"]
    pts, cols, planes, trail = synthetic_corridor()
    base = f"memory/synthetic-{rid}"
    p1 = (await put_object(f"{base}/points.f32", pts.tobytes(), "application/octet-stream")).get("path") or f"between-visit/{base}/points.f32"
    p3 = (await put_object(f"{base}/colors.u8", cols.tobytes(), "application/octet-stream")).get("path") or f"between-visit/{base}/colors.u8"
    meta = json.dumps({"planes": planes, "trail": trail, "metres_walked": 16.0}).encode()
    p2 = (await put_object(f"{base}/memory.json", meta, "application/json")).get("path") or f"between-visit/{base}/memory.json"
    mem = RouteMemory(route_id=rid, teach_session_id="synthetic", points_path=p1, json_path=p2, point_count=len(pts), plane_count=len(planes), trail_m=16.0)
    doc = {**mem.to_mongo(), "colors_path": p3, "label": "Synthetic 3D model"}
    await db.route_memories.insert_one(doc)
    old = await db.route_versions.distinct("memory_id", {"route_id": rid})
    await db.route_versions.update_many({"route_id": rid}, {"$set": {"memory_id": mem.id}})
    cps = {"Entrance": [0.0, 0.0, 0.0], "Hallway turn": [0.0, 0.0, -9.9], "Reception desk": [6.0, 0.0, -10.0]}
    for name, p in cps.items():
        await db.checkpoints.update_one({"route_id": rid, "name": name}, {"$set": {"position": p}})
    chair = await db.route_versions.update_one({"route_id": rid, "version": 2, "known_entities.label": "chair"}, {"$set": {"known_entities.$.position": list(DEMO_CHAIR)}})
    rec = await db.recordings.find_one({"route_id": rid, "kind": "synthetic"}, {"_id": 0, "id": 1, "frames": 1})
    if rec and len(rec["frames"]) > 2:
        await db.recordings.update_one({"id": rec["id"]}, {"$set": {"frames.2.depth.centre": 3.1, "model_label": "Synthetic 3D model"}})
    result = {"route": rid, "memory": mem.id, "points": len(pts), "replaced": old, "chair_set": chair.modified_count, "recording_adjusted": bool(rec)}
    await db.migrations.insert_one({"id": marker, "created_at": now_iso(), "result": result})
    logger.info("%s: %s", marker, result)


DEMO_LANDMARKS = {
    # source frame (1-based, synthetic recording); Sonnet distinctiveness suggestion edited to ≤25 words and to close-range features
    "Entrance": (1, "Start of the route: the metal handrail begins on the left wall and the yellow tactile strip starts, leading toward grey push-bar double doors."),
    "Hallway turn": (8, "A RECEPTION sign with an arrow on the right-hand corner, where the yellow tactile strip branches off to the right into a side corridor."),
    "Reception desk": (12, "A wooden reception counter across the end of the side corridor, with a RECEPTION sign above the door behind it; the tactile strip ends here."),
}


async def phase19_demo_landmarks():
    """One-off, user-approved: distinct landmark texts + own-frame photos for the 3D demo route (checkpoints + v1 and v2). Past events untouched."""
    from models import Photo
    from storage import get_object, put_object
    from vision import process_image
    marker = "phase19-demo-landmarks"
    if await db.migrations.find_one({"id": marker}):
        return await _demo_texts_current()
    route = await db.routes.find_one({"name": DEMO_3D_NEW}, {"_id": 0, "id": 1})
    rec = await db.recordings.find_one({"route_id": route["id"], "kind": "synthetic"}, {"_id": 0}) if route else None
    if not rec:
        return
    rid, result = route["id"], {"checkpoints": [], "versions": 0, "old_photos_unservable": []}
    for cp in await db.checkpoints.find({"route_id": rid}, {"_id": 0}).to_list(50):
        if cp["name"] not in DEMO_LANDMARKS:
            continue
        frame, text = DEMO_LANDMARKS[cp["name"]]
        jpeg, w, h = process_image(await get_object(rec["frames"][frame - 1]["path"]))
        photo = Photo(checkpoint_id=cp["id"], route_id=rid, storage_path="", width=w, height=h, size=len(jpeg))
        photo.storage_path = (await put_object(f"checkpoints/{photo.id}.jpg", jpeg, "image/jpeg"))["path"]
        await db.photos.insert_one(photo.to_mongo())
        url = f"/api/photos/{photo.id}"
        await db.checkpoints.update_one({"id": cp["id"]}, {"$set": {"photo_url": url, "landmark_text": text, "ai_suggested": True, "ai_unavailable": False, "updated_at": now_iso()}})
        r = await db.route_versions.update_many({"route_id": rid}, {"$set": {"checkpoints.$[c].photo_url": url, "checkpoints.$[c].landmark_text": text}}, array_filters=[{"c.id": cp["id"]}])
        result["versions"] = max(result["versions"], r.modified_count)
        if cp.get("photo_url"):
            old = cp["photo_url"].rsplit("/", 1)[1]
            await db.photos.update_one({"id": old}, {"$set": {"is_deleted": True}})
            result["old_photos_unservable"].append(old)
        result["checkpoints"].append({"name": cp["name"], "frame": frame, "photo": photo.id, "words": len(text.split())})
    await db.migrations.insert_one({"id": marker, "applied_at": now_iso(), "result": result})
    logger.info("%s: %s", marker, result)


async def _demo_texts_current():
    """Keeps the fixed demo texts in place (checkpoints + all versions); logs only when something changed."""
    route = await db.routes.find_one({"name": DEMO_3D_NEW}, {"_id": 0, "id": 1})
    if not route:
        return
    changed = []
    for cp in await db.checkpoints.find({"route_id": route["id"], "name": {"$in": list(DEMO_LANDMARKS)}}, {"_id": 0}).to_list(50):
        text = DEMO_LANDMARKS[cp["name"]][1]
        r = await db.route_versions.update_many({"route_id": route["id"]}, {"$set": {"checkpoints.$[c].landmark_text": text}}, array_filters=[{"c.id": cp["id"], "c.landmark_text": {"$ne": text}}])
        if cp["landmark_text"] != text or r.modified_count:
            await db.checkpoints.update_one({"id": cp["id"]}, {"$set": {"landmark_text": text, "updated_at": now_iso()}})
            changed.append(cp["name"])
    if changed:
        logger.info("phase19-demo-landmarks texts updated: %s", changed)
