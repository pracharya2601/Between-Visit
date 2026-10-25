from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, StringConstraints

from db import db
from models import Checkpoint, CheckpointSnapshot, Client, Photo, Route, RouteVersion
from storage import get_object, put_object
from vision import MAX_UPLOAD_BYTES, RETAKE, process_image, suggest_landmark

AUTHOR = "J. Rivera (synthetic)"

router = APIRouter(prefix="/api")


class RouteSummary(Route):
    checkpoint_count: int


class RouteDetail(Route):
    checkpoints: List[Checkpoint]


class RouteUpdate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CheckpointUpdate(BaseModel):
    name: Optional[str] = None
    landmark_text: Optional[str] = None


class MoveIn(BaseModel):
    direction: Literal["up", "down"]


class PhotoResult(BaseModel):
    ai_status: Literal["suggested", "retake", "unavailable"]
    message: str
    checkpoint: Checkpoint


async def get_route(route_id: str) -> Route:
    doc = await db.routes.find_one({"id": route_id, "is_test": {"$ne": True}}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Route not found")
    return Route.from_mongo(doc)


async def get_checkpoint(checkpoint_id: str) -> Checkpoint:
    doc = await db.checkpoints.find_one({"id": checkpoint_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    return Checkpoint.from_mongo(doc)


async def route_checkpoints(route_id: str) -> List[Checkpoint]:
    docs = await db.checkpoints.find({"route_id": route_id}, {"_id": 0}).sort("order", 1).to_list(1000)
    return [Checkpoint.from_mongo(d) for d in docs]


async def renumber(route_id: str):
    for i, cp in enumerate(await route_checkpoints(route_id), start=1):
        if cp.order != i:
            await db.checkpoints.update_one({"id": cp.id}, {"$set": {"order": i}})


async def set_checkpoint(cp_id: str, changes: dict) -> Checkpoint:
    await db.checkpoints.update_one({"id": cp_id}, {"$set": changes})
    return await get_checkpoint(cp_id)


@router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str):
    doc = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client.from_mongo(doc)


@router.get("/routes", response_model=List[RouteSummary])
async def list_routes():
    routes = [Route.from_mongo(d) for d in await db.routes.find({"is_test": {"$ne": True}, "teach_pending": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(1000)]
    return [
        RouteSummary(**r.model_dump(), checkpoint_count=await db.checkpoints.count_documents({"route_id": r.id}))
        for r in routes
    ]


@router.post("/routes", response_model=Route, status_code=201)
async def create_route(body: RouteUpdate):
    practice = await db.practices.find_one({}, {"_id": 0, "id": 1})
    route = Route(practice_id=practice["id"], name=body.name)
    await db.routes.insert_one(route.to_mongo())
    return route


@router.get("/routes/{route_id}", response_model=RouteDetail)
async def route_detail(route_id: str):
    route = await get_route(route_id)
    return RouteDetail(**route.model_dump(), checkpoints=await route_checkpoints(route_id))


@router.patch("/routes/{route_id}", response_model=Route)
async def rename_route(route_id: str, body: RouteUpdate):
    await get_route(route_id)
    await db.routes.update_one({"id": route_id}, {"$set": {"name": body.name}})
    return await get_route(route_id)


@router.post("/routes/{route_id}/checkpoints", response_model=Checkpoint, status_code=201)
async def add_checkpoint(route_id: str):
    await get_route(route_id)
    cp = Checkpoint(route_id=route_id, order=await db.checkpoints.count_documents({"route_id": route_id}) + 1)
    await db.checkpoints.insert_one(cp.to_mongo())
    return cp


@router.patch("/checkpoints/{checkpoint_id}", response_model=Checkpoint)
async def update_checkpoint(checkpoint_id: str, body: CheckpointUpdate):
    cp = await get_checkpoint(checkpoint_id)
    changes = {}
    if body.name is not None and body.name != cp.name:
        changes["name"] = body.name
    if body.landmark_text is not None and body.landmark_text != cp.landmark_text:
        changes.update(landmark_text=body.landmark_text, ai_suggested=False)
    if not changes:
        return cp
    return await set_checkpoint(checkpoint_id, {**changes, "approved": False})


@router.delete("/checkpoints/{checkpoint_id}", status_code=204)
async def remove_checkpoint(checkpoint_id: str):
    cp = await get_checkpoint(checkpoint_id)
    await db.checkpoints.delete_one({"id": checkpoint_id})
    await renumber(cp.route_id)
    return Response(status_code=204)


@router.post("/checkpoints/{checkpoint_id}/move", response_model=List[Checkpoint])
async def move_checkpoint(checkpoint_id: str, body: MoveIn):
    cp = await get_checkpoint(checkpoint_id)
    cps = await route_checkpoints(cp.route_id)
    i = next(i for i, c in enumerate(cps) if c.id == cp.id)
    j = i - 1 if body.direction == "up" else i + 1
    if not 0 <= j < len(cps):
        raise HTTPException(status_code=422, detail=f"Can't move {body.direction}")
    await db.checkpoints.update_one({"id": cps[i].id}, {"$set": {"order": j + 1}})
    await db.checkpoints.update_one({"id": cps[j].id}, {"$set": {"order": i + 1}})
    return await route_checkpoints(cp.route_id)


@router.post("/checkpoints/{checkpoint_id}/approve", response_model=Checkpoint)
async def approve_checkpoint(checkpoint_id: str):
    cp = await get_checkpoint(checkpoint_id)
    if not (cp.name.strip() and cp.photo_url and cp.landmark_text.strip()):
        raise HTTPException(status_code=422, detail="Add a name, a photo and landmark text before approving")
    return await set_checkpoint(checkpoint_id, {"approved": True})


@router.post("/checkpoints/{checkpoint_id}/photo", response_model=PhotoResult)
async def upload_photo(checkpoint_id: str, file: UploadFile = File(...)):
    cp = await get_checkpoint(checkpoint_id)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Photo is over 15 MB. Choose a smaller photo.")
    try:
        jpeg, width, height = process_image(data)
    except ValueError:
        raise HTTPException(status_code=415, detail="That file isn't an image. Choose a photo.")
    del data
    status, text = await suggest_landmark(jpeg)
    if status == "retake":
        return PhotoResult(ai_status="retake", message=RETAKE, checkpoint=cp)
    try:
        updated = await attach_photo(cp.id, jpeg, width, height, status, text)
    except Exception:
        raise HTTPException(status_code=502, detail="Couldn't store the photo. Try again.")
    message = "Suggested by AI" if status == "suggested" else "AI suggestion unavailable"
    return PhotoResult(ai_status=status, message=message, checkpoint=updated)


async def attach_photo(cp_id: str, jpeg: bytes, width: int, height: int, status: str, text: Optional[str]) -> Checkpoint:
    """Stores an accepted (person-free) checkpoint photo and sets the AI text; used by upload and teach walks."""
    cp = await get_checkpoint(cp_id)
    photo = Photo(checkpoint_id=cp_id, route_id=cp.route_id, storage_path="", width=width, height=height, size=len(jpeg))
    stored = await put_object(f"checkpoints/{photo.id}.jpg", jpeg, "image/jpeg")
    photo.storage_path = stored["path"]
    await db.photos.insert_one(photo.to_mongo())
    changes = {"photo_url": f"/api/photos/{photo.id}", "approved": False, "needs_photo": False, "photo_pending": False, "ai_unavailable": status != "suggested"}
    if status == "suggested":
        changes.update(landmark_text=text, ai_suggested=True)
    return await set_checkpoint(cp_id, changes)


@router.get("/photos/{photo_id}")
async def serve_photo(photo_id: str):
    doc = await db.photos.find_one({"id": photo_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = Photo.from_mongo(doc)
    data = await get_object(photo.storage_path)
    return Response(content=data, media_type=photo.content_type, headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.post("/routes/{route_id}/save", response_model=RouteVersion, status_code=201)
async def save_route(route_id: str):
    route = await get_route(route_id)
    cps = await route_checkpoints(route_id)
    if not route.name.strip():
        raise HTTPException(status_code=422, detail="Add a route name")
    if not cps:
        raise HTTPException(status_code=422, detail="Add at least one checkpoint")
    if not all(c.approved for c in cps):
        raise HTTPException(status_code=422, detail="Approve every checkpoint")
    prev = await db.route_versions.find_one({"route_id": route_id}, {"_id": 0, "memory_id": 1, "known_entities": 1}, sort=[("version", -1)])
    prev = prev or {}
    return await create_version(route, cps, prev.get("memory_id"), prev.get("known_entities") or [])


async def create_version(route: Route, cps: List[Checkpoint], memory_id: Optional[str], known_entities: Optional[list] = None) -> RouteVersion:
    version = RouteVersion(
        route_id=route.id,
        version=route.current_version + 1,
        checkpoints=[CheckpointSnapshot(id=c.id, order=c.order, name=c.name, photo_url=c.photo_url, landmark_text=c.landmark_text) for c in cps],
        author=AUTHOR,
        memory_id=memory_id,
        known_entities=known_entities or [],
        note="route saved" if route.current_version == 0 else "checkpoints edited",
    )
    await db.route_versions.insert_one(version.to_mongo())
    await db.routes.update_one({"id": route.id}, {"$set": {"current_version": version.version}})
    return version


@router.get("/routes/{route_id}/versions", response_model=List[RouteVersion])
async def list_versions(route_id: str):
    docs = await db.route_versions.find({"route_id": route_id}, {"_id": 0}).sort("version", 1).to_list(1000)
    return [RouteVersion.from_mongo(d) for d in docs]
