import logging
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
