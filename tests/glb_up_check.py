"""Checks .glb scans default to +y up while .ply still uses guess_up. Usage: python3 glb_up_check.py"""
import os
import numpy as np
import requests
import trimesh
from pathlib import Path

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
OUT = Path("/app/tests/.glbup")
OUT.mkdir(exist_ok=True)


def room():
    box = trimesh.creation.box(extents=(8.0, 3.0, 2.5))
    keep = box.face_normals[:, 1] > -0.9  # drop the -y faces, keep +y: no floor/ceiling pair along y
    keep &= box.face_normals[:, 2] < 0.9  # drop the +z face: floor without ceiling along z
    keep[box.face_normals[:, 1] > 0.9] = False  # and drop +y too so y is symmetric
    m = trimesh.Trimesh(box.vertices, box.faces[keep])
    m = m.subdivide().subdivide().subdivide()
    return m


def run(path: Path):
    size = path.stat().st_size
    s = requests.post(f"{API}/scans", json={"route_name": f"Check up {path.suffix}", "empty_space": True, "filename": path.name, "size": size}).json()
    with open(path, "rb") as f:
        off = 0
        while chunk := f.read(4 * 1024 * 1024):
            requests.put(f"{API}/scans/{s['id']}/chunk", params={"offset": off}, data=chunk, headers={"Content-Type": "application/octet-stream"}).raise_for_status()
            off += len(chunk)
    v = requests.post(f"{API}/scans/{s['id']}/process", timeout=300).json()
    return s["id"], v


if __name__ == "__main__":
    m = room()
    from scan import guess_up, sample_points  # noqa: E402
    glb, ply = OUT / "longroom.glb", OUT / "longroom.ply"
    m.export(glb)
    m.export(ply)
    _, nrm, _, _ = sample_points(glb, ".glb")
    print("guess_up on this geometry would pick:", guess_up(nrm))
    for p in (glb, ply):
        sid, v = run(p)
        print(p.suffix, "scan", sid, "up =", v.get("up"), "auto_up =", v.get("auto_up"), "status", v.get("status"))
    for p in (glb, ply):
        os.remove(p)
    OUT.rmdir()
