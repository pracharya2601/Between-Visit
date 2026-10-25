"""Backend API checks for Phase 18 — 3D scan upload / create / size limits."""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://route-checkpoints.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def created_scan_ids():
    ids = []
    yield ids
    for sid in ids:
        try:
            requests.post(f"{BASE}/api/scans/{sid}/cancel", timeout=10)
        except Exception:
            pass


class TestScanCreateValidation:
    def test_empty_space_false_returns_422(self, created_scan_ids):
        r = requests.post(f"{BASE}/api/scans", json={
            "route_name": "TEST_phase18_empty",
            "empty_space": False,
            "filename": "corridor.glb",
            "size": 1000,
        }, timeout=10)
        assert r.status_code == 422, r.text
        detail = r.json().get("detail", "")
        assert "empty space" in detail.lower() or "no people" in detail.lower()

    def test_wrong_extension_returns_415(self, created_scan_ids):
        r = requests.post(f"{BASE}/api/scans", json={
            "route_name": "TEST_phase18_txt",
            "empty_space": True,
            "filename": "notes.txt",
            "size": 1000,
        }, timeout=10)
        assert r.status_code == 415, r.text
        assert ".glb" in r.json().get("detail", "")

    def test_too_big_returns_413(self, created_scan_ids):
        r = requests.post(f"{BASE}/api/scans", json={
            "route_name": "TEST_phase18_big",
            "empty_space": True,
            "filename": "huge.glb",
            "size": 101 * 1024 * 1024,
        }, timeout=10)
        assert r.status_code == 413, r.text
        assert "100 MB" in r.json().get("detail", "")

    def test_valid_create_201(self, created_scan_ids):
        r = requests.post(f"{BASE}/api/scans", json={
            "route_name": "TEST_phase18_valid",
            "empty_space": True,
            "filename": "corridor.glb",
            "size": 50_000,
        }, timeout=10)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["route_name"] == "TEST_phase18_valid"
        assert data["status"] == "uploading"
        assert "id" in data
        created_scan_ids.append(data["id"])
        # Verify GET
        g = requests.get(f"{BASE}/api/scans/{data['id']}", timeout=10)
        assert g.status_code == 200
        assert g.json()["id"] == data["id"]
