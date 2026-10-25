"""Create a route from a practitioner's 3D scan: chunked upload to local temp disk only → points → placement → v1."""
import asyncio
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import List, Literal, Optional

import numpy as np
import trimesh
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from db import db
from migrations import delete_routes_cascade
from models import Checkpoint, Route, RouteMemory, ScanSession, now_iso
from storage import put_object
from workspace import create_version, route_checkpoints

router = APIRouter(prefix="/api")

SCAN_DIR = Path(tempfile.gettempdir()) / "bv_scans"
MAX_BYTES = 100 * 1024 * 1024
MAX_CHUNK = 16 * 1024 * 1024
POINTS = 150_000
EXTS = (".glb", ".ply", ".obj")
LABEL = "3D scan (uploaded by practitioner)"
UNITS = {"m": 1.0, "cm": 0.01, "mm": 0.001}
UPS = ["+y", "+z", "-z", "+x", "-x", "-y"]
UP_ROT = {
    "+y": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "-y": [[1, 0, 0], [0, -1, 0], [0, 0, -1]],
    "+z": [[1, 0, 0], [0, 0, 1], [0, -1, 0]], "-z": [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
    "+x": [[0, -1, 0], [1, 0, 0], [0, 0, 1]], "-x": [[0, 1, 0], [-1, 0, 0], [0, 0, 1]],
}
STALE_S = 6 * 3600
NO_GEOMETRY = "This file has no 3D geometry we can use."
UNREADABLE = "We couldn't read this file as a 3D model. Export it again as .glb, .ply or .obj."
TOO_BIG = "This file is over 100 MB. Export a smaller scan (lower detail or a shorter area)."
WRONG_TYPE = "Choose a .glb, .ply or .obj file."


class ScanError(Exception):
    pass


class ScanIn(BaseModel):
    route_name: str = Field(min_length=1)
    empty_space: bool
    filename: str
    size: int


class OrientIn(BaseModel):
    unit: Optional[Literal["m", "cm", "mm"]] = None
    turn_upright: bool = False


class PlacePoint(BaseModel):
    name: str = ""
    x: float
    z: float


class PlaceIn(BaseModel):
    facing: List[float] = Field(min_length=2, max_length=2)
    points: List[PlacePoint] = Field(min_length=2, max_length=30)


def upload_path(s: ScanSession) -> Path:
    return SCAN_DIR / f"{s.id}{s.ext}"


def points_path(scan_id: str) -> Path:
    return SCAN_DIR / f"{scan_id}.npz"


def remove_files(scan_id: str):
    for p in SCAN_DIR.glob(f"{scan_id}*"):
        p.unlink(missing_ok=True)


def sweep_scan_files() -> int:
    """Startup/creation sweep: temp files older than 6 h are removed (abandoned uploads)."""
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in SCAN_DIR.iterdir():
        if time.time() - p.stat().st_mtime > STALE_S:
            p.unlink(missing_ok=True)
            n += 1
    return n


def _texture(m: trimesh.Trimesh):
    mat = getattr(m.visual, "material", None)
    return getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)


def _colour_source(m: trimesh.Trimesh) -> Optional[str]:
    v = m.visual
    if v.kind == "texture" and getattr(v, "uv", None) is not None and _texture(m) is not None:
        return "texture"
    if v.kind in ("vertex", "face"):
        return "vertex"
    return None


def _texture_colours(m: trimesh.Trimesh, n: int, seed: int):
    p, fi, bary = trimesh.sample.sample_surface(m, n, return_barycentric=True, seed=seed)
    uv = (np.asarray(m.visual.uv)[m.faces[fi]] * bary[:, :, None]).sum(axis=1)
    return p, fi, trimesh.visual.color.uv_to_interpolated_color(uv, _texture(m))


def _parts(path: Path, ext: str):
    try:
        loaded = trimesh.load(str(path), file_type=ext.lstrip("."), process=False)
    except Exception:
        raise ScanError(UNREADABLE)
    items = []
    if isinstance(loaded, trimesh.Scene):
        for node in loaded.graph.nodes_geometry:
            transform, name = loaded.graph[node]
            items.append((loaded.geometry[name], transform))
    else:
        items.append((loaded, None))
    meshes, clouds = [], []
    for g, t in items:
        if isinstance(g, trimesh.Trimesh) and len(g.faces) and g.area > 0:
            g = g.copy()
            if t is not None:
                g.apply_transform(t)
            meshes.append(g)
        elif isinstance(g, trimesh.PointCloud) and len(g.vertices):
            if t is not None:
                g = g.copy()
                g.apply_transform(t)
            clouds.append(g)
    if not meshes and not clouds:
        raise ScanError(NO_GEOMETRY)
    return meshes, clouds


def sample_points(path: Path, ext: str):
    """~150k surface points with normals and colours (vertex → texture → none = height colours in the browser)."""
    meshes, clouds = _parts(path, ext)
    pts, nrm, cols, sources = [], [], [], set()
    total = sum(m.area for m in meshes)
    for i, m in enumerate(meshes):
        n = max(1, round(POINTS * m.area / total))
        src = _colour_source(m)
        c = None
        if src == "texture":
            try:
                p, fi, c = _texture_colours(m, n, i)
            except Exception:
                p, fi = trimesh.sample.sample_surface(m, n, seed=i)
                src = None
        else:
            p, fi = trimesh.sample.sample_surface(m, n, seed=i)
            if src == "vertex":
                c = m.visual.face_colors[fi]
        pts.append(p)
        nrm.append(m.face_normals[fi])
        cols.append(np.asarray(c)[:, :3].astype(np.int16) if c is not None else np.full((len(p), 3), -1, np.int16))
        if src:
            sources.add(src)
    for c in clouds:
        v = np.asarray(c.vertices)
        keep = np.linspace(0, len(v) - 1, min(len(v), POINTS)).astype(np.int64)
        pts.append(v[keep])
        nrm.append(np.zeros((len(keep), 3)))
        cc = np.asarray(c.colors) if c.colors is not None and len(c.colors) == len(v) else None
        cols.append(cc[keep, :3].astype(np.int16) if cc is not None else np.full((len(keep), 3), -1, np.int16))
        if cc is not None:
            sources.add("vertex")
    pts, nrm, cols = np.vstack(pts), np.vstack(nrm), np.vstack(cols)
    if not np.isfinite(pts).all() or np.ptp(pts, axis=0).max() <= 0:
        raise ScanError(NO_GEOMETRY)
    known = cols[:, 0] >= 0
    if not known.any() or cols[known].std(axis=0).max() < 2:
        cols, source = np.zeros((0, 3), np.uint8), None
    else:
        cols[~known] = 150
        cols, source = cols.astype(np.uint8), "texture" if "texture" in sources else "vertex"
    return pts.astype(np.float32), nrm.astype(np.float16), cols, source


def guess_unit(pts: np.ndarray) -> str:
    longest = float(np.ptp(pts, axis=0).max())
    return "mm" if longest > 2500 else "cm" if longest > 60 else "m"


def guess_up(nrm: np.ndarray) -> str:
    """The axis whose surfaces face one way most (a floor without its ceiling); +Y (glTF convention) when unclear."""
    n = nrm.astype(np.float32)
    best, axis = 0.0, "+y"
    for a, name in enumerate("xyz"):
        asym = float((n[:, a] > 0.9).mean() - (n[:, a] < -0.9).mean())
        if abs(asym) > abs(best):
            best, axis = asym, ("+" if asym > 0 else "-") + name
    return axis if abs(best) > 0.05 else "+y"


def display_frame(raw, s: ScanSession):
    """Scaled + upright points with the floor at y=0 and the footprint centred; returns (pts, floor_y_raw_offset)."""
    pts = raw["pts"].astype(np.float64) * UNITS[s.unit] @ np.asarray(UP_ROT[s.up], dtype=np.float64).T
    nrm = raw["nrm"].astype(np.float32) @ np.asarray(UP_ROT[s.up], dtype=np.float32).T
    up = pts[nrm[:, 1] > 0.9, 1]
    if len(up) >= 100:
        bins = np.floor((up - up.min()) / 0.05).astype(np.int64)
        counts = np.bincount(bins)
        floor = up.min() + (int(np.argmax(counts >= 0.2 * counts.max())) + 0.5) * 0.05
    else:
        floor = float(np.percentile(pts[:, 1], 1))
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    pts -= [(lo[0] + hi[0]) / 2, floor, (lo[2] + hi[2]) / 2]
    return pts


def placement_rotation(facing) -> tuple:
    fx, fz = facing
    phi = -math.pi / 2 - math.atan2(fz, fx)
    return math.cos(phi), math.sin(phi)


def place_frame(pts: np.ndarray, placed: dict) -> np.ndarray:
    """Entrance → (0,0,0) on the floor, facing → −Z."""
    ex, ez = placed["entrance"]
    c, s = placed["rotation"]
    dx, dz = pts[:, 0] - ex, pts[:, 2] - ez
    return np.stack([c * dx - s * dz, pts[:, 1], s * dx + c * dz], axis=1)


def size_of(pts: np.ndarray) -> dict:
    lo, hi = np.percentile(pts, 1, axis=0), np.percentile(pts, 99, axis=0)
    x, y, z = (float(round(v, 1)) for v in hi - lo)
    return {"x": x, "y": y, "z": z, "text": f"about {max(x, z):g} × {min(x, z):g} m, {y:g} m high"}


def load_raw(scan_id: str):
    p = points_path(scan_id)
    if not p.exists():
        raise HTTPException(status_code=410, detail="This scan's points are gone. Upload the scan again.")
    return np.load(p)


async def get_scan(scan_id: str) -> ScanSession:
    doc = await db.scan_sessions.find_one({"id": scan_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanSession.from_mongo(doc)


async def set_scan(scan_id: str, changes: dict) -> ScanSession:
    await db.scan_sessions.update_one({"id": scan_id}, {"$set": {**changes, "updated_at": now_iso()}})
    return await get_scan(scan_id)


async def fail(s: ScanSession, status_code: int, message: str):
    remove_files(s.id)
    await set_scan(s.id, {"status": "failed", "error": message})
    raise HTTPException(status_code=status_code, detail=message)


async def view(s: ScanSession) -> dict:
    out = {k: getattr(s, k) for k in ("id", "route_id", "route_name", "filename", "size", "received", "status", "error", "unit", "auto_unit", "up", "auto_up", "colour_source", "point_count", "memory_id")}
    out["scene"] = None
    if s.status in ("ready", "placed") and points_path(s.id).exists():
        pts = await asyncio.to_thread(lambda: display_frame(load_raw(s.id), s))
        out["dimensions"] = size_of(pts)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        cps = await route_checkpoints(s.route_id) if s.status == "placed" else []
        trail = (s.placed or {}).get("trail") or []
        out["scene"] = {"points": s.point_count, "points_sent": s.point_count, "planes": [], "trail": trail, "metres_walked": (s.placed or {}).get("metres", 0.0),
                        "bounds": [[float(lo[0]), 0.0, float(lo[2])], [float(hi[0]), 0.0, float(hi[2])]],
                        "checkpoints": [{"id": c.id, "order": c.order, "name": c.name, "position": c.position} for c in cps]}
    return out


@router.post("/scans", status_code=201)
async def create_scan(body: ScanIn):
    if not body.empty_space:
        raise HTTPException(status_code=422, detail="Tick “I scanned an empty space (no people)” before uploading.")
    ext = os.path.splitext(body.filename.lower())[1]
    if ext not in EXTS:
        raise HTTPException(status_code=415, detail=WRONG_TYPE)
    if body.size > MAX_BYTES:
        raise HTTPException(status_code=413, detail=TOO_BIG)
    if body.size <= 0:
        raise HTTPException(status_code=422, detail=NO_GEOMETRY)
    sweep_scan_files()
    practice = await db.practices.find_one({}, {"_id": 0, "id": 1})
    route = Route(practice_id=practice["id"], name=body.route_name.strip(), teach_pending=True)
    await db.routes.insert_one(route.to_mongo())
    s = ScanSession(route_id=route.id, route_name=route.name, filename=os.path.basename(body.filename), ext=ext, size=body.size)
    await db.scan_sessions.insert_one(s.to_mongo())
    upload_path(s).touch()
    return await view(s)


@router.get("/scans/{scan_id}")
async def scan_view(scan_id: str):
    return await view(await get_scan(scan_id))


@router.put("/scans/{scan_id}/chunk")
async def upload_chunk(scan_id: str, offset: int, request: Request):
    s = await get_scan(scan_id)
    if s.status != "uploading":
        raise HTTPException(status_code=409, detail="This upload has already finished.")
    data = await request.body()
    if len(data) > MAX_CHUNK or offset != s.received:
        raise HTTPException(status_code=422, detail="Upload chunk out of order. Start the upload again.")
    if s.received + len(data) > min(s.size, MAX_BYTES):
        await fail(s, 413, TOO_BIG if s.received + len(data) > MAX_BYTES else "The file is bigger than it said it was. Start the upload again.")
    if offset == 0 and s.ext == ".glb" and data[:4] != b"glTF":
        await fail(s, 415, UNREADABLE)
    with open(upload_path(s), "ab") as f:
        f.write(data)
    s = await set_scan(scan_id, {"received": s.received + len(data)})
    return {"received": s.received, "size": s.size}


@router.post("/scans/{scan_id}/process")
async def process_scan(scan_id: str):
    s = await get_scan(scan_id)
    if s.status != "uploading" or s.received != s.size:
        raise HTTPException(status_code=409, detail="Finish uploading the file first.")
    await set_scan(scan_id, {"status": "processing"})
    t0 = time.time()
    try:
        pts, nrm, cols, source = await asyncio.to_thread(sample_points, upload_path(s), s.ext)
    except ScanError as e:
        await fail(s, 422, str(e))
    except Exception:
        await fail(s, 422, UNREADABLE)
    finally:
        upload_path(s).unlink(missing_ok=True)
    np.savez(points_path(scan_id), pts=pts, nrm=nrm, cols=cols)
    unit, up = guess_unit(pts), "+y" if s.ext == ".glb" else guess_up(nrm)
    s = await set_scan(scan_id, {"status": "ready", "unit": unit, "auto_unit": unit, "up": up, "auto_up": up, "colour_source": source,
                                 "point_count": len(pts), "seconds": round(time.time() - t0, 1)})
    return await view(s)


@router.post("/scans/{scan_id}/orient")
async def orient_scan(scan_id: str, body: OrientIn):
    s = await get_scan(scan_id)
    if s.status != "ready":
        raise HTTPException(status_code=409, detail="Units and upright can only change before placement is confirmed.")
    changes = {}
    if body.unit:
        changes["unit"] = body.unit
    if body.turn_upright:
        changes["up"] = UPS[(UPS.index(s.up) + 1) % len(UPS)]
    return await view(await set_scan(scan_id, changes))


@router.get("/scans/{scan_id}/points")
async def scan_points(scan_id: str):
    s = await get_scan(scan_id)
    pts = await asyncio.to_thread(lambda: _frame_points_sync(s))
    return Response(content=pts.astype("<f4").tobytes(), media_type="application/octet-stream", headers={"X-Point-Count": str(len(pts)), "Cache-Control": "no-store"})


def _frame_points_sync(s: ScanSession) -> np.ndarray:
    pts = display_frame(load_raw(s.id), s)
    return place_frame(pts, s.placed) if s.status == "placed" and s.placed else pts


@router.get("/scans/{scan_id}/colors")
async def scan_colors(scan_id: str):
    s = await get_scan(scan_id)
    cols = load_raw(s.id)["cols"]
    if not len(cols):
        raise HTTPException(status_code=404, detail="This scan has no colours")
    return Response(content=cols.tobytes(), media_type="application/octet-stream", headers={"Cache-Control": "no-store"})


@router.post("/scans/{scan_id}/place")
async def place_scan(scan_id: str, body: PlaceIn):
    s = await get_scan(scan_id)
    if s.status != "ready":
        raise HTTPException(status_code=409, detail="Placement was already confirmed.")
    if math.hypot(*body.facing) < 1e-6:
        raise HTTPException(status_code=422, detail="Drag from the Entrance to set the facing direction.")
    c, sn = placement_rotation(body.facing)
    e = body.points[0]
    placed = {"entrance": [e.x, e.z], "facing": body.facing, "rotation": [c, sn]}
    xyz = place_frame(np.array([[p.x, 0.0, p.z] for p in body.points]), placed)
    trail = [[round(float(x), 3), 0.0, round(float(z), 3)] for x, _, z in xyz]
    metres = round(sum(math.dist(a, b) for a, b in zip(trail, trail[1:])), 2)
    await db.checkpoints.delete_many({"route_id": s.route_id})
    for i, (p, pos) in enumerate(zip(body.points, trail), start=1):
        name = p.name.strip() or ("Entrance" if i == 1 else f"Checkpoint {i}")
        await db.checkpoints.insert_one(Checkpoint(route_id=s.route_id, order=i, name=name, position=pos).to_mongo())
    s = await set_scan(scan_id, {"status": "placed", "placed": {**placed, "trail": trail, "metres": metres}})
    return await view(s)


@router.post("/scans/{scan_id}/save")
async def save_scan(scan_id: str):
    s = await get_scan(scan_id)
    if s.status != "placed":
        raise HTTPException(status_code=409, detail="Confirm the placement first.")
    cps = await route_checkpoints(s.route_id)
    if not all(c.approved for c in cps):
        raise HTTPException(status_code=422, detail="Approve every checkpoint")
    raw = load_raw(s.id)
    pts = await asyncio.to_thread(_frame_points_sync, s)
    trail, metres = s.placed["trail"], s.placed["metres"]
    p1 = (await put_object(f"memory/scan-{s.id}/points.f32", pts.astype("<f4").tobytes(), "application/octet-stream"))["path"]
    p2 = (await put_object(f"memory/scan-{s.id}/memory.json", json.dumps({"planes": [], "trail": trail, "metres_walked": metres, "source": "scan"}).encode(), "application/json"))["path"]
    p3 = (await put_object(f"memory/scan-{s.id}/colors.u8", raw["cols"].tobytes(), "application/octet-stream"))["path"] if len(raw["cols"]) else None
    mem = RouteMemory(route_id=s.route_id, teach_session_id=s.id, points_path=p1, json_path=p2, point_count=len(pts), plane_count=0, trail_m=metres,
                      colors_path=p3, label=LABEL, kind="scan")
    await db.route_memories.insert_one(mem.to_mongo())
    route = Route.from_mongo(await db.routes.find_one({"id": s.route_id}, {"_id": 0}))
    version = await create_version(route, cps, mem.id)
    await db.routes.update_one({"id": route.id}, {"$set": {"teach_pending": False}})
    remove_files(s.id)
    await set_scan(scan_id, {"status": "saved", "memory_id": mem.id})
    return {"version": version.version, "route_id": route.id, "memory_id": mem.id, "label": LABEL}


@router.post("/scans/{scan_id}/cancel")
async def cancel_scan(scan_id: str):
    s = await get_scan(scan_id)
    if s.status == "saved":
        raise HTTPException(status_code=409, detail="This scan route is already saved.")
    remove_files(s.id)
    gone = await delete_routes_cascade([s.route_id])
    await set_scan(scan_id, {"status": "cancelled"})
    return {"status": "cancelled", "photos_unservable": gone["photos_unservable"]}
