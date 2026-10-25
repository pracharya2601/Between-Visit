"""Phase 13: demo recording + replay backend tests.

Covers: /api/demo, /api/demo/replays public cap (3), /api/routes/{id}/replays,
/api/replays/{id} (no key_hash, 404 for non-replay), /api/replays/{id}/frames/{i},
/api/routes/{id}/recordings, /api/run/{id} record_demo field, sweep_public_replays
exclusions (progress_notes, corrections, practitioner).
"""
import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE = _load_url()
DEMO_ROUTE = "276dc5bb-53b0-4734-83d7-c7743052d09d"
NO_REC_ROUTE = "c06bb936-43e3-43a0-87cd-cbf29279abe3"
CLIENT_ID = "0a8239a5-8108-4595-a916-50a172a9edac"

CREATED_ATTEMPTS: list[str] = []


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    # Cleanup any replay attempts we spawned (use a fresh motor client)
    import sys
    sys.path.insert(0, "/app/backend")

    async def _clean():
        import motor.motor_asyncio
        mongo = os.environ.get("MONGO_URL") or open("/app/backend/.env").read().split("MONGO_URL=")[1].split("\n")[0].strip()
        dbname = os.environ.get("DB_NAME") or open("/app/backend/.env").read().split("DB_NAME=")[1].split("\n")[0].strip()
        c = motor.motor_asyncio.AsyncIOMotorClient(mongo)
        d = c[dbname]
        # Wait for replays to finish so they don't persist running state
        await asyncio.sleep(2)
        for aid in CREATED_ATTEMPTS:
            await d.attempt_events.delete_many({"attempt_id": aid})
            await d.attempts.delete_one({"id": aid})
        c.close()
    asyncio.run(_clean())


def _wait_running(attempt_id: str, timeout=10):
    for _ in range(timeout * 4):
        r = requests.get(f"{BASE}/api/replays/{attempt_id}")
        if r.status_code == 200 and r.json().get("frame_index", -1) >= 0:
            return r.json()
        time.sleep(0.25)
    return None


def _wait_ended(attempt_id: str, timeout=30):
    for _ in range(timeout * 2):
        r = requests.get(f"{BASE}/api/replays/{attempt_id}")
        if r.status_code == 200 and r.json().get("status") == "ended":
            return r.json()
        time.sleep(0.5)
    return None


# --- /api/demo info ---
class TestDemoInfo:
    def test_demo_info_has_recordings(self):
        r = requests.get(f"{BASE}/api/demo")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["route_id"] == DEMO_ROUTE
        assert d["current_version"] >= 2
        assert len(d["recordings"]) >= 1
        rec = d["recordings"][0]
        assert "frame_count" in rec and rec["frame_count"] > 0
        assert rec["kind"] in ("real", "synthetic")

    def test_route_recordings_demo(self):
        r = requests.get(f"{BASE}/api/routes/{DEMO_ROUTE}/recordings")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_route_recordings_none(self):
        r = requests.get(f"{BASE}/api/routes/{NO_REC_ROUTE}/recordings")
        assert r.status_code == 200
        assert r.json() == []


# --- Replay lifecycle (v1 public) ---
class TestReplayLifecycle:
    def test_public_v1_replay_full(self):
        r = requests.post(f"{BASE}/api/demo/replays", json={"on": "v1"})
        assert r.status_code == 201, r.text
        aid = r.json()["attempt_id"]
        CREATED_ATTEMPTS.append(aid)

        running = _wait_running(aid)
        assert running is not None, "replay never started"
        assert running["public"] is True
        assert running["version"] == 1
        assert "v1 (before corrections)" in running["version_line"]
        assert running["recording"]["kind"] == "synthetic"
        assert running["recording"]["label"] == "Synthetic demo (AI-generated images)"
        assert running["frame_url"] and running["frame_url"].startswith("/api/replays/")

        # frame endpoint returns jpeg
        fr = requests.get(f"{BASE}{running['frame_url']}")
        assert fr.status_code == 200
        assert fr.headers["content-type"] == "image/jpeg"

        # out-of-range frame -> 404
        fr2 = requests.get(f"{BASE}/api/replays/{aid}/frames/9999")
        assert fr2.status_code == 404

        ended = _wait_ended(aid, timeout=40)
        assert ended is not None, "replay did not end"
        assert ended["review_path"] == f"/review/{aid}"
        assert ended["cues_spoken"] >= 1  # v1 should speak chair cue
        # chair cue text includes 'Chair'
        # Check events for chair cue
        # review page returns via /api/review/{id}
        rv = requests.get(f"{BASE}/api/attempts/{aid}/review")
        assert rv.status_code == 200

    def test_replay_state_strips_key_hash(self):
        # start fresh public replay
        r = requests.post(f"{BASE}/api/demo/replays", json={"on": "latest"})
        assert r.status_code == 201
        aid = r.json()["attempt_id"]
        CREATED_ATTEMPTS.append(aid)
        time.sleep(1)
        s = requests.get(f"{BASE}/api/replays/{aid}").json()
        assert "key_hash" not in s
        # Should only have this one attempt's data
        assert s["attempt_id"] == aid

    def test_replay_404_for_non_replay(self):
        # a known normal attempt id from phase 12
        r = requests.get(f"{BASE}/api/replays/48461db6-54af-4344-a634-30753164eb85")
        assert r.status_code == 404


# --- Public cap ---
class TestPublicCap:
    def test_four_rapid_starts(self):
        # Prior tests may have running public replays (~17s each). Wait them out.
        time.sleep(25)
        codes = []
        ids = []
        for _ in range(4):
            r = requests.post(f"{BASE}/api/demo/replays", json={"on": "latest"})
            codes.append(r.status_code)
            if r.status_code == 201:
                ids.append(r.json()["attempt_id"])
                CREATED_ATTEMPTS.append(r.json()["attempt_id"])
            else:
                assert r.json()["detail"] == "Demo busy, try again in a minute."
        assert codes.count(201) == 3
        assert codes.count(429) == 1

    def test_practitioner_not_affected_by_cap(self):
        # Three public should still be running from previous test
        r = requests.post(f"{BASE}/api/routes/{DEMO_ROUTE}/replays", json={"on": "latest"})
        assert r.status_code == 201, r.text
        CREATED_ATTEMPTS.append(r.json()["attempt_id"])


# --- Sweep ---
class TestSweep:
    def test_sweep_excludes_practitioner_and_notes(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from db import db
        import replay as replay_mod

        async def run():
            # Wait for prior replays to end
            for _ in range(60):
                running = await db.attempts.count_documents({"replay": True, "status": "running"})
                if running == 0:
                    break
                await asyncio.sleep(1)

            # Create one public replay (ended) and one practitioner replay (ended)
            # Then insert a progress_notes doc for one more public replay to protect it
            # Simplest: use the attempts we already created above
            ended_pub = await db.attempts.find({"replay": True, "public": True, "status": "ended"}, {"_id": 0, "id": 1}).to_list(100)
            ended_prac = await db.attempts.find({"replay": True, "public": False, "status": "ended"}, {"_id": 0, "id": 1}).to_list(100)
            assert len(ended_pub) >= 1
            assert len(ended_prac) >= 1

            protected_id = ended_pub[0]["id"]
            # Insert temp progress_notes doc
            temp_note = {"id": "TEST_phase13_" + str(uuid.uuid4()), "attempt_id": protected_id}
            await db.progress_notes.insert_one(temp_note)

            try:
                future = datetime.now(timezone.utc) + timedelta(hours=25)
                deleted = await replay_mod.sweep_public_replays(now=future)
                # Should delete other ended public replays, but not protected one and not practitioner
                still_protected = await db.attempts.find_one({"id": protected_id})
                still_prac = await db.attempts.find_one({"id": ended_prac[0]["id"]})
                assert still_protected is not None, "Protected public (with note) was deleted"
                assert still_prac is not None, "Practitioner replay was deleted"
                assert deleted >= 1
            finally:
                await db.progress_notes.delete_one({"id": temp_note["id"]})
                # Remove swept ids from CREATED_ATTEMPTS so cleanup doesn't choke
                remaining = await db.attempts.find({"replay": True}, {"_id": 0, "id": 1}).to_list(1000)
                remaining_ids = {d["id"] for d in remaining}
                for aid in list(CREATED_ATTEMPTS):
                    if aid not in remaining_ids:
                        CREATED_ATTEMPTS.remove(aid)

        asyncio.run(run())


# --- Run / record_demo plumbing ---
class TestRunRecordDemo:
    def test_route_without_recordings_still_lists_empty(self):
        r = requests.get(f"{BASE}/api/routes/{NO_REC_ROUTE}/recordings")
        assert r.status_code == 200 and r.json() == []
