import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import List

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from db import db, mongo
from ingest import TEST_STREAM_ID, hash_key, install_log_filter
from ingest import router as ingest_router
from workspace import router as workspace_router
from exercises import router as exercises_router
from migrations import phase4_cleanup, phase4_model_updates, phase5_cleanup, phase6_cleanup
from run import router as run_router
from models import (
    COLLECTIONS,
    FOREIGN_KEYS,
    Attempt,
    Client,
    Exercise,
    Practice,
    Practitioner,
    Route,
    TestConfig,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
install_log_filter()


async def ensure_indexes():
    for name in COLLECTIONS:
        await db[name].create_index("id", unique=True)
    for name, fields in FOREIGN_KEYS.items():
        for field in fields:
            await db[name].create_index(field)
    await db.attempts.create_index("stream_id", unique=True)
    await db.test_config.create_index("stream_id", unique=True)
    await db.route_versions.create_index([("route_id", 1), ("version", 1)], unique=True)
    await db.attempt_events.create_index([("attempt_id", 1), ("type", 1), ("seq", 1)])


async def reset_unsaved_route_versions():
    saved = await db.route_versions.distinct("route_id")
    await db.routes.update_many({"id": {"$nin": saved}, "current_version": {"$ne": 0}}, {"$set": {"current_version": 0}})


async def seed():
    if await db.practices.count_documents({}) > 0:
        logger.info("Seed skipped: practices already present")
        return
    practice = Practice(name="Bay Mobility Practice")
    practitioner = Practitioner(practice_id=practice.id, name="J. Rivera (synthetic)", role="O&M specialist")
    clients = [
        Client(practice_id=practice.id, display_name="Client A (synthetic)", notes="Synthetic profile. Practices indoor routes.", synthetic=True),
        Client(practice_id=practice.id, display_name="Client B (synthetic)", notes="Synthetic profile. Practices street crossings.", synthetic=True),
    ]
    await db.practices.insert_one(practice.to_mongo())
    await db.practitioners.insert_one(practitioner.to_mongo())
    await db.clients.insert_many([c.to_mongo() for c in clients])
    logger.info("Seed inserted: 1 practice, 1 practitioner, 2 clients")


async def seed_test_attempt():
    if await db.attempts.find_one({"stream_id": TEST_STREAM_ID}):
        logger.info("Test attempt seed skipped: already present")
        return
    client_a = Client.from_mongo(await db.clients.find_one({"display_name": "Client A (synthetic)"}, {"_id": 0}))
    route = Route(practice_id=client_a.practice_id, name="Test route (synthetic)", is_test=True)
    exercise = Exercise(route_id=route.id, route_version=0, client_id=client_a.id, goal="Device ingest test (synthetic)", cue_style="standard")
    key = secrets.token_urlsafe(24)
    attempt = Attempt(exercise_id=exercise.id, status="pending", stream_id=TEST_STREAM_ID, key_hash=hash_key(key))
    await db.routes.insert_one(route.to_mongo())
    await db.exercises.insert_one(exercise.to_mongo())
    await db.attempts.insert_one(attempt.to_mongo())
    await db.test_config.insert_one(TestConfig(stream_id=TEST_STREAM_ID, attempt_id=attempt.id, key=key).to_mongo())
    logger.info("Test attempt seeded: 1 route, 1 exercise, 1 attempt")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    await seed()
    await seed_test_attempt()
    await reset_unsaved_route_versions()
    await phase4_model_updates()
    await phase4_cleanup()
    await phase5_cleanup()
    await phase6_cleanup()
    yield
    mongo.close()


app = FastAPI(title="Between Visit API", openapi_url="/api/openapi.json", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)
api_router = APIRouter(prefix="/api")


@api_router.get("/health")
async def health():
    return {"ok": True}


@api_router.get("/practices", response_model=List[Practice])
async def list_practices():
    return [Practice.from_mongo(d) for d in await db.practices.find({}, {"_id": 0}).to_list(1000)]


@api_router.get("/practitioners", response_model=List[Practitioner])
async def list_practitioners():
    return [Practitioner.from_mongo(d) for d in await db.practitioners.find({}, {"_id": 0}).to_list(1000)]


@api_router.get("/clients", response_model=List[Client])
async def list_clients():
    return [Client.from_mongo(d) for d in await db.clients.find({}, {"_id": 0}).to_list(1000)]


app.include_router(api_router)
app.include_router(ingest_router)
app.include_router(workspace_router)
app.include_router(exercises_router)
app.include_router(run_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
