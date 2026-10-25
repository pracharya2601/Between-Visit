"""Distinct-landmark checker shared by the route builder, teach review and scan placement: flags checkpoint pairs that read or look alike."""
import asyncio
import io
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel

from db import db
from storage import get_object
from vision import RETAKE, suggest_landmark
from workspace import get_checkpoint, route_checkpoints, set_checkpoint

router = APIRouter(prefix="/api")

TEXT_JACCARD = 0.6
HASH_HAMMING = 10
STOPWORDS = set("""a an the and or but of to in on at by for with from into onto over under along across toward towards
up down left right ahead here there this that these those it its is are was be been has have had with without
as near next beside past then just very more most some any each one two three your you there's it's
""".split())
HASHES: dict = {}
MESSAGE = "Reads like {who}. Add what is different here (a sign, a door, a turn, a sound)."


def content_words(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words if w not in STOPWORDS and len(w) > 1}


def jaccard(a: str, b: str) -> float:
    x, y = content_words(a), content_words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def dhash(data: bytes) -> int:
    img = Image.open(io.BytesIO(data)).convert("L").resize((9, 8), Image.LANCZOS)
    px = list(img.getdata())
    return sum(1 << i for i in range(64) if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])


async def photo_hash(photo_url: Optional[str]) -> Optional[int]:
    if not photo_url or not photo_url.startswith("/api/photos/"):
        return None
    pid = photo_url.rsplit("/", 1)[1]
    if pid not in HASHES:
        doc = await db.photos.find_one({"id": pid, "is_deleted": {"$ne": True}}, {"_id": 0, "storage_path": 1})
        if not doc:
            return None
        HASHES[pid] = await asyncio.to_thread(dhash, await get_object(doc["storage_path"]))
    return HASHES[pid]


def who(orders: list) -> str:
    orders = sorted(orders)
    if len(orders) == 1:
        return f"checkpoint {orders[0]}"
    return "checkpoints " + ", ".join(map(str, orders[:-1])) + f" and {orders[-1]}"


def alike_pairs(items: list) -> list:
    """items: [{id, order, text, hash}] -> [(i, j, why)] for pairs too alike (text overlap or photo hash)."""
    out = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            why = []
            if jaccard(a["text"], b["text"]) >= TEXT_JACCARD:
                why.append("text")
            if a.get("hash") is not None and b.get("hash") is not None and bin(a["hash"] ^ b["hash"]).count("1") <= HASH_HAMMING:
                why.append("photo")
            if why:
                out.append((i, j, why))
    return out


class SimilarityItem(BaseModel):
    id: str
    order: int
    landmark_text: str = ""
    photo_url: Optional[str] = None


class SimilarityIn(BaseModel):
    checkpoints: List[SimilarityItem]


async def warnings_for(cps: list) -> dict:
    items = [{"id": c.id, "order": c.order, "text": c.landmark_text, "hash": await photo_hash(c.photo_url)} for c in cps]
    alike: dict = {}
    for i, j, why in alike_pairs(items):
        a, b = items[i], items[j]
        alike.setdefault(a["id"], {"orders": [], "why": set()})["orders"].append(b["order"])
        alike.setdefault(b["id"], {"orders": [], "why": set()})["orders"].append(a["order"])
        alike[a["id"]]["why"].update(why)
        alike[b["id"]]["why"].update(why)
    return {k: {"orders": sorted(v["orders"]), "why": sorted(v["why"]), "message": MESSAGE.format(who=who(v["orders"]))} for k, v in alike.items()}


@router.post("/checkpoints/similarity")
async def similarity(body: SimilarityIn):
    return {"warnings": await warnings_for(body.checkpoints)}


@router.post("/checkpoints/{checkpoint_id}/suggest-distinct")
async def suggest_distinct(checkpoint_id: str):
    cp = await get_checkpoint(checkpoint_id)
    if not cp.photo_url:
        raise HTTPException(status_code=422, detail="Add a photo first.")
    doc = await db.photos.find_one({"id": cp.photo_url.rsplit("/", 1)[1]}, {"_id": 0, "storage_path": 1})
    if not doc:
        raise HTTPException(status_code=422, detail="Add a photo first.")
    others = [(c.order, c.landmark_text) for c in await route_checkpoints(cp.route_id) if c.id != cp.id and c.landmark_text.strip()]
    status, text = await suggest_landmark(await get_object(doc["storage_path"]), others)
    if status == "retake":
        return {"ai_status": "retake", "message": RETAKE, "checkpoint": cp}
    if status != "suggested":
        return {"ai_status": "unavailable", "message": "AI suggestion unavailable", "checkpoint": cp}
    updated = await set_checkpoint(cp.id, {"landmark_text": text, "ai_suggested": True, "ai_unavailable": False, "approved": False})
    return {"ai_status": "suggested", "message": "Suggested by AI", "checkpoint": updated}
