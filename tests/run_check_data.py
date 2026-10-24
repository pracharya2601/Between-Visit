"""Creates or deletes temporary run-check data. Usage: python3 run_check_data.py setup|cleanup"""
import asyncio
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, "/app/backend")
from db import db  # noqa: E402
from migrations import delete_routes_cascade  # noqa: E402
from models import CheckpointSnapshot, Route, RouteVersion  # noqa: E402

STATE = Path("/app/tests/.run_check.json")
NAME = "Run check (synthetic)"
API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
H = {"User-Agent": "between-visit-check/1.0"}


async def setup():
    practice = await db.practices.find_one({}, {"_id": 0, "id": 1})
    client_a = await db.clients.find_one({"display_name": "Client A (synthetic)"}, {"_id": 0, "id": 1})
    route = Route(practice_id=practice["id"], name=NAME, current_version=1)
    cps = [CheckpointSnapshot(id=f"cp{i}", order=i, name=n, photo_url="/api/photos/none", landmark_text="synthetic") for i, n in enumerate(["Entrance doors", "Handrail end", "Reception desk"], 1)]
    await db.routes.insert_one(route.to_mongo())
    await db.route_versions.insert_one(RouteVersion(route_id=route.id, version=1, checkpoints=cps, author="J. Rivera (synthetic)").to_mongo())
    body = {"client_id": client_a["id"], "goal": "Walk from the entrance to the reception desk using the three landmarks", "stop_rule": "If you feel unsure, stop, press Help and wait for my call."}
    first = requests.post(f"{API}/routes/{route.id}/exercises", json=body, headers=H).json()
    second = requests.post(f"{API}/exercises/{first['exercise']['id']}/attempts", headers=H).json()
    data = {"route_id": route.id, "client_id": client_a["id"], "attempts": [
        {"id": x["attempt"]["id"], "stream_id": x["attempt"]["stream_id"], "key": x["key"]} for x in (first, second)]}
    STATE.write_text(json.dumps(data))
    print(json.dumps(data, indent=1))


async def cleanup():
    data = json.loads(STATE.read_text())
    print(await delete_routes_cascade([data["route_id"]]))
    STATE.unlink()


asyncio.run(setup() if sys.argv[1] == "setup" else cleanup())
