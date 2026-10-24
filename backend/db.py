import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")

mongo = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = mongo[os.environ["DB_NAME"]]
