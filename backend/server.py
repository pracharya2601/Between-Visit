import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

from models import COLLECTIONS, FOREIGN_KEYS, Client, Practice, Practitioner

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo[os.environ["DB_NAME"]]


async def ensure_indexes():
    for name in COLLECTIONS:
        await db[name].create_index("id", unique=True)
    for name, fields in FOREIGN_KEYS.items():
        for field in fields:
            await db[name].create_index(field)


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


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    await seed()
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
