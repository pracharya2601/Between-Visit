"""Phase 12 targeted checks: progress note endpoints + machine-view/memory endpoint."""
import os
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ATT_3D = "48461db6-54af-4344-a634-30753164eb85"
ATT_2D = "a59b1526-6c85-4c7b-992f-2854fd908502"
ROUTE_3D = "276dc5bb-53b0-4734-83d7-c7743052d09d"
ROUTE_2D = "c06bb936-43e3-43a0-87cd-cbf29279abe3"
CLIENT_A = "0a8239a5-8108-4595-a916-50a172a9edac"


# ---------- Progress note endpoints ----------
def test_draft_on_already_saved_attempt_409():
    r = requests.post(f"{BASE}/api/attempts/{ATT_3D}/note/draft")
    assert r.status_code == 409, r.text
    assert "already has a saved note" in r.json()["detail"]


def test_save_note_on_already_saved_attempt_409():
    r = requests.post(f"{BASE}/api/attempts/{ATT_3D}/note",
                      json={"draft_id": "nope", "text": "hi"})
    assert r.status_code == 409, r.text


def test_draft_unknown_attempt_404():
    r = requests.post(f"{BASE}/api/attempts/nope/note/draft")
    assert r.status_code == 404, r.text


def test_notes_methods_not_allowed():
    # Get saved note first
    g = requests.get(f"{BASE}/api/attempts/{ATT_3D}/note")
    assert g.status_code == 200
    note_id = g.json()["note"]["id"]
    for m in ("put", "patch", "delete"):
        r = getattr(requests, m)(f"{BASE}/api/notes/{note_id}")
        assert r.status_code == 405, f"{m} /notes/{{id}} -> {r.status_code}"
    for m in ("put", "patch", "delete"):
        r = getattr(requests, m)(f"{BASE}/api/attempts/{ATT_3D}/note")
        assert r.status_code == 405, f"{m} /attempts/{{id}}/note -> {r.status_code}"


def test_get_saved_note_schema():
    r = requests.get(f"{BASE}/api/attempts/{ATT_3D}/note")
    assert r.status_code == 200
    n = r.json()["note"]
    for k in ("id", "attempt_id", "client_id", "text", "ai_draft", "model",
             "author", "approved_at", "route_name", "route_version",
             "attempt_date", "client_name"):
        assert k in n, f"missing {k}"
    assert n["author"] == "J. Rivera (synthetic)"
    assert n["model"] == "claude-sonnet-5-5"
    # Six headings present
    for h in ["Summary", "Checkpoints reached",
              "Cues (spoken / held back, with main reasons)",
              "Help requests", "Observations",
              "Suggested focus for the next session"]:
        assert h in n["text"], f"heading {h!r} missing"


def test_client_notes_list():
    r = requests.get(f"{BASE}/api/clients/{CLIENT_A}/notes")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) >= 1
    found = [n for n in items if n["attempt_id"] == ATT_3D]
    assert found, "expected 3D demo note in client A list"
    n = found[0]
    assert n["route_name"] == "Review demo route 3D (synthetic)"
    assert n["route_version"] == 1
    assert n["client_name"] == "Client A (synthetic)"


def test_single_note_endpoint():
    g = requests.get(f"{BASE}/api/attempts/{ATT_3D}/note")
    nid = g.json()["note"]["id"]
    r = requests.get(f"{BASE}/api/notes/{nid}")
    assert r.status_code == 200
    assert r.json()["id"] == nid


def test_single_note_404():
    r = requests.get(f"{BASE}/api/notes/does-not-exist")
    assert r.status_code == 404


# ---------- Machine view / route memory endpoint ----------
def test_memory_3d_v2():
    r = requests.get(f"{BASE}/api/routes/{ROUTE_3D}/memory")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "BetweenVisit route memory"
    assert body["authoritative"] is False
    assert body["route_id"] == ROUTE_3D
    assert body["version"] == 2
    # Checkpoint positions present (3D), first one ~0,0,0
    cps = body["checkpoints"]
    assert len(cps) >= 1
    first = cps[0]["position"]
    assert first is not None
    assert first["units"] == "m" and first["origin"] == "route_start"
    assert abs(first["x"]) < 0.01 and abs(first["y"]) < 0.01 and abs(first["z"]) < 0.01
    # entities contains the chair
    ents = body["entities"]
    chairs = [e for e in ents if e["entity"]["label"] == "chair"]
    assert chairs, "no chair entity found"
    c = chairs[0]
    assert c["type"] == "REPLAN_LEFT"
    assert c["authoritative"] is False
    assert c["source"] == "BetweenVisit route memory"
    assert c["route_id"] == ROUTE_3D
    assert c["version"] == 2
    e = c["entity"]
    assert e["label"] == "chair"
    assert e["side"] == "ahead"
    assert e["segment"] == {"from": 1, "to": 2}
    assert e["position"] is None
    assert "verified_by" in e and "verified_at" in e
    assert c["advice"] == "Reported chair ahead on the path; keep left."
    # No photo/points/planes/trail/keys leakage
    forbidden = {"photo", "points", "planes", "trail", "keys", "photo_url", "image_url"}
    assert not (forbidden & set(body.keys()))
    for cp in cps:
        assert not (forbidden & set(cp.keys()))


def test_memory_3d_v1_no_entities():
    r = requests.get(f"{BASE}/api/routes/{ROUTE_3D}/memory?version=1")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1
    assert body["entities"] == []


def test_memory_3d_v99_404():
    r = requests.get(f"{BASE}/api/routes/{ROUTE_3D}/memory?version=99")
    assert r.status_code == 404


def test_memory_unknown_route_404():
    r = requests.get(f"{BASE}/api/routes/does-not-exist/memory")
    assert r.status_code == 404


def test_memory_test_route_hidden_404():
    # Test route (is_test=True) must be hidden
    r = requests.get(f"{BASE}/api/routes/82d7438a-96de-4970-afbc-8f4a8bdd8207/memory")
    assert r.status_code == 404


def test_memory_2d_null_positions():
    r = requests.get(f"{BASE}/api/routes/{ROUTE_2D}/memory")
    assert r.status_code == 200
    body = r.json()
    cps = body["checkpoints"]
    assert len(cps) >= 1
    # 2D route has no 3D memory -> positions all null
    for cp in cps:
        assert cp["position"] is None, f"2D route checkpoint has position: {cp}"


# ---------- Run page/API never shows notes/machine data ----------
def test_run_endpoint_no_notes_or_machine():
    # Attempt run endpoint response schema should not contain note/machine
    r = requests.get(f"{BASE}/api/attempts/{ATT_3D}/run")
    # It's fine if 404/409 (ended), but if 200 ensure no notes/machine leak
    if r.status_code == 200:
        body = r.json()
        import json
        s = json.dumps(body)
        assert "progress_note" not in s and "ai_draft" not in s
        assert '"machine"' not in s
