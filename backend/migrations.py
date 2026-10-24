import logging

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


async def phase4_model_updates():
    await db.routes.update_many({"name": TEST_ROUTE, "is_test": {"$ne": True}}, {"$set": {"is_test": True}})
    await db.exercises.update_many(
        {"silence_rules": {"$type": "string"}},
        {"$set": {"silence_rules": {"stay_silent_on_route": True, "no_repeat": True, "note": None}}},
    )
    await db.exercises.update_many({"route_version": {"$exists": False}}, {"$set": {"route_version": 0}})
