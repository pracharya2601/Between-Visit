"""Phase 15: 3D replay backend tests."""
import os
import requests
import pytest

def _load_env():
    try:
        with open("/app/frontend/.env") as f:
            for ln in f:
                if ln.startswith("REACT_APP_BACKEND_URL="):
                    return ln.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

BASE = _load_env()
ROUTE_ID = "276dc5bb-53b0-4734-83d7-c7743052d09d"
ATT_IIRI = "48461db6-54af-4344-a634-30753164eb85"


def test_memory_v2_chair_position():
    r = requests.get(f"{BASE}/api/routes/{ROUTE_ID}/memory?version=2", timeout=15)
    assert r.status_code == 200
    data = r.json()
    # Find chair in known entities
    ents = data.get("known_entities") or data.get("entities") or []
    # try other shapes
    found = None
    def scan(obj):
        nonlocal found
        if isinstance(obj, dict):
            lbl = str(obj.get("label", "")).lower()
            if "chair" in lbl and ("x" in obj or "pos" in obj or "position" in obj):
                found = obj
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
    scan(data)
    assert found is not None, f"No chair entity found in memory v2: {data}"
    # extract x,z
    pos = found.get("position") or found.get("pos") or found
    if isinstance(pos, (list, tuple)):
        x, z = pos[0], pos[-1]
    else:
        x = pos.get("x")
        z = pos.get("z")
    assert abs(x - 0.6) < 0.01, f"chair x={x} expected 0.6"
    assert abs(z - (-5.0)) < 0.01, f"chair z={z} expected -5.0"


def test_review_colors_binary():
    r = requests.get(f"{BASE}/api/attempts/{ATT_IIRI}/review/colors", timeout=20)
    assert r.status_code == 200
    assert len(r.content) % 3 == 0, f"colors length {len(r.content)} not multiple of 3"
    assert len(r.content) > 0


def test_replays_points_and_colors():
    # Need a replay attempt. Create one on demo v1.
    body = {"version": 1}
    r = requests.post(f"{BASE}/api/demo/replays", json=body, timeout=15)
    assert r.status_code in (200, 201), r.text
    aid = r.json()["attempt_id"]
    try:
        pts = requests.get(f"{BASE}/api/replays/{aid}/points", timeout=20)
        assert pts.status_code == 200
        assert len(pts.content) % 12 == 0, f"points len {len(pts.content)}"
        n_points = len(pts.content) // 12

        cols = requests.get(f"{BASE}/api/replays/{aid}/points?colors=true", timeout=20)
        assert cols.status_code == 200
        assert len(cols.content) % 3 == 0
        n_colors = len(cols.content) // 3
        assert n_points == n_colors, f"points {n_points} != colors {n_colors}"
        # Spec: 38540 points
        assert n_points == 38540, f"expected 38540 synthetic points, got {n_points}"
    finally:
        # cleanup via admin? just leave; test cleanup script handles.
        pass
    return aid
