"""Phase 18 test meshes in /tmp/scan_tests: coloured corridor .glb (vertex + texture), cm .obj, Z-up .ply, empty .glb, fake .glb, large ~70 MB .glb."""
import json
import struct
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

OUT = Path("/tmp/scan_tests")
OUT.mkdir(exist_ok=True)


def quad(corners, rgb, normal):
    """Single-sided surface like a phone scan (faces the scanner, i.e. into the room)."""
    v = np.asarray(corners, float)
    f = np.array([[0, 1, 2], [0, 2, 3]])
    if np.dot(np.cross(v[1] - v[0], v[2] - v[0]), normal) < 0:
        f = f[:, ::-1]
    m = trimesh.Trimesh(v, f, process=False)
    m.visual.vertex_colors = np.tile([*rgb, 255], (4, 1))
    return m


def box(extents, centre, rgb):
    m = trimesh.creation.box(extents=extents)
    m.apply_translation(centre)
    m.visual.vertex_colors = np.tile([*rgb, 255], (len(m.vertices), 1))
    return m


def floor_q(x0, x1, z0, z1, rgb, y=0.0):
    return quad([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]], rgb, [0, 1, 0])


def wall_q(a, b, h, rgb, normal):
    (x0, z0), (x1, z1) = a, b
    return quad([[x0, 0, z0], [x1, 0, z1], [x1, h, z1], [x0, h, z0]], rgb, [normal[0], 0, normal[1]])


def corridor_parts():
    """10 m corridor along −Z from (0,0,0), 1.8 m wide, then a 6 m leg to +X with a reception desk; single-sided surfaces, no ceiling."""
    floor, wall, strip = (120, 110, 100), (225, 215, 190), (240, 200, 0)
    return [
        floor_q(-0.9, 0.9, 1.0, -10.9, floor), floor_q(0.9, 6.9, -9.1, -10.9, floor),
        wall_q((-0.9, 1.0), (-0.9, -10.9), 2.6, wall, (1, 0)), wall_q((0.9, 1.0), (0.9, -9.1), 2.6, wall, (-1, 0)),
        wall_q((-0.9, -10.9), (6.9, -10.9), 2.6, wall, (0, 1)), wall_q((0.9, -9.1), (6.9, -9.1), 2.6, wall, (0, -1)),
        wall_q((6.9, -9.1), (6.9, -10.9), 2.6, (200, 205, 215), (-1, 0)),
        floor_q(-0.65, -0.35, 0.0, -10.0, strip, 0.005),
        box([0.05, 0.05, 9.0], [-0.85, 0.9, -5.0], (90, 90, 95)),
        box([0.9, 2.1, 0.06], [0, 1.05, 0.95], (170, 40, 40)),
        box([1.6, 1.05, 0.7], [5.6, 0.525, -10.3], (140, 90, 50)),
        box([0.45, 0.9, 0.45], [0.6, 0.45, -6.5], (30, 90, 160)),
    ]


def poster():
    img = Image.new("RGB", (256, 256), (20, 60, 140))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 236, 236], outline=(255, 255, 255), width=10)
    d.text((70, 110), "RECEPTION", fill=(255, 255, 255))
    m = trimesh.creation.box(extents=[1.2, 0.8, 0.02])
    uv = np.c_[(m.vertices[:, 0] + 0.6) / 1.2, (m.vertices[:, 1] + 0.4) / 0.8]
    m.visual = trimesh.visual.TextureVisuals(uv=uv, image=img)
    m.apply_translation([4.5, 1.7, -10.88])
    return m


def corridor_glb():
    scene = trimesh.Scene(corridor_parts() + [poster()])
    (OUT / "corridor.glb").write_bytes(scene.export(file_type="glb"))


def room_parts(w=4.2, d=3.1, h=2.5):
    g, c = (120, 110, 100), (225, 215, 190)
    return [floor_q(-w / 2, w / 2, d / 2, -d / 2, g), wall_q((-w / 2, d / 2), (-w / 2, -d / 2), h, c, (1, 0)), wall_q((w / 2, d / 2), (w / 2, -d / 2), h, c, (-1, 0)),
            wall_q((-w / 2, -d / 2), (w / 2, -d / 2), h, c, (0, 1)), box([1.2, 0.75, 0.6], [1.0, 0.375, -1.0], (140, 90, 50))]


def room_cm_obj():
    m = trimesh.util.concatenate(room_parts())
    m.apply_scale(100)
    m.visual = trimesh.visual.ColorVisuals()
    (OUT / "room_cm.obj").write_text(m.export(file_type="obj"))


def room_zup_ply():
    m = trimesh.util.concatenate(room_parts(4.0, 3.0, 2.5))
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    (OUT / "room_zup.ply").write_bytes(m.export(file_type="ply"))


def empty_glb():
    js = json.dumps({"asset": {"version": "2.0"}, "scenes": [{"nodes": []}], "scene": 0}).encode()
    js += b" " * (-len(js) % 4)
    (OUT / "empty.glb").write_bytes(b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js)) + struct.pack("<I", len(js)) + b"JSON" + js)
    (OUT / "fake.glb").write_text("this is a text file renamed to .glb\n")


def large_glb(target_mb=100):
    parts = []
    for p in corridor_parts():
        p = p.subdivide_to_size(max_edge=0.03, max_iter=12) if p.area > 0.5 else p
        parts.append(p)
    m = trimesh.util.concatenate(parts)
    rng = np.random.default_rng(1)
    m.vertices += rng.normal(0, 0.004, m.vertices.shape)
    while len(m.faces) * 4 * 12 + len(m.vertices) * 4 * 16 < target_mb * 1e6:
        m = m.subdivide()
    noise = Image.fromarray(np.random.default_rng(2).integers(0, 255, (4096, 4096, 3), dtype=np.uint8))
    wall = trimesh.creation.box(extents=[4.0, 2.4, 0.02])
    wall.visual = trimesh.visual.TextureVisuals(uv=np.c_[(wall.vertices[:, 0] + 2) / 4, (wall.vertices[:, 1] + 1.2) / 2.4], image=noise)
    wall.apply_translation([3.4, 1.3, -10.85])
    (OUT / "large.glb").write_bytes(trimesh.Scene([m, wall]).export(file_type="glb"))


if __name__ == "__main__":
    which = sys.argv[1:] or ["small", "large"]
    if "small" in which:
        corridor_glb(); room_cm_obj(); room_zup_ply(); empty_glb()
    if "large" in which:
        large_glb()
    for f in sorted(OUT.iterdir()):
        print(f.name, round(f.stat().st_size / 1e6, 1), "MB")
