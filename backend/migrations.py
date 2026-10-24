import logging

from db import db
from models import now_iso
from storage import delete_object

logger = logging.getLogger(__name__)

CHECK_ROUTES = ["Check route (synthetic)", "Library entrance (synthetic)"]
TEST_ROUTE = "Test route (synthetic)"


async def phase4_cleanup():
    if await db.migrations.find_one({"id": "phase4-cleanup"}):
        return
    route_ids = await db.routes.distinct("id", {"name": {"$in": CHECK_ROUTES}, "is_test": {"$ne": True}})
    cp_ids = await db.checkpoints.distinct("id", {"route_id": {"$in": route_ids}})
    photos = await db.photos.find({"checkpoint_id": {"$in": cp_ids}}, {"_id": 0, "id": 1, "storage_path": 1}).to_list(10000)
    deleted_in_storage = 0
    for p in photos:
        ok = await delete_object(p["storage_path"])
        deleted_in_storage += ok
        await db.photos.update_one({"id": p["id"]}, {"$set": {"is_deleted": True, "storage_deleted": ok}})
    result = {
        "routes": (await db.routes.delete_many({"id": {"$in": route_ids}})).deleted_count,
        "checkpoints": (await db.checkpoints.delete_many({"id": {"$in": cp_ids}})).deleted_count,
        "route_versions": (await db.route_versions.delete_many({"route_id": {"$in": route_ids}})).deleted_count,
        "photos_unservable": len(photos),
        "photos_deleted_in_storage": deleted_in_storage,
    }
    await db.migrations.insert_one({"id": "phase4-cleanup", "created_at": now_iso(), "result": result})
    logger.info("Phase 4 cleanup: %s", result)


async def phase4_model_updates():
    await db.routes.update_many({"name": TEST_ROUTE, "is_test": {"$ne": True}}, {"$set": {"is_test": True}})
    await db.exercises.update_many(
        {"silence_rules": {"$type": "string"}},
        {"$set": {"silence_rules": {"stay_silent_on_route": True, "no_repeat": True, "note": None}}},
    )
    await db.exercises.update_many({"route_version": {"$exists": False}}, {"$set": {"route_version": 0}})
