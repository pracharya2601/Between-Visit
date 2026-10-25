"""Phase 19 temporary data for the browser checks (prints ids). `python3 p19_seed.py` / `python3 p19_seed.py cleanup`."""
import asyncio
import io
import sys

import requests

sys.path.insert(0, "/app/backend")
from db import db  # noqa: E402
from storage import get_object  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
SAME = "A yellow tactile paving strip runs down the corridor centre to a push-bar door, with a metal handrail on the left wall."
NEAR = "A yellow tactile paving strip runs down the corridor center to a push-bar exit door, with a metal handrail along the left wall."


async def frame(i):
    rec = await db.recordings.find_one({"route_id": "276dc5bb-53b0-4734-83d7-c7743052d09d", "kind": "synthetic"}, {"_id": 0})
    return await get_object(rec["frames"][i]["path"])


async def add_cps(route_id, specs):
    for i, (name, fi, text) in enumerate(specs):
        cp = requests.post(f"{API}/routes/{route_id}/checkpoints").json()
        requests.post(f"{API}/checkpoints/{cp['id']}/photo", files={"file": (f"f{fi}.jpg", io.BytesIO(await frame(fi)), "image/jpeg")})
        requests.patch(f"{API}/checkpoints/{cp['id']}", json={"name": name, "landmark_text": text})


async def seed():
    r = requests.post(f"{API}/routes", json={"name": "TEMP P19 builder"}).json()
    await add_cps(r["id"], [("Door end", 0, SAME), ("Chair spot", 3, NEAR), ("Desk", 11, "A wooden reception counter at the end of the side corridor.")])
    t = requests.post(f"{API}/teach", json={"route_name": "TEMP P19 teach"}).json()
    await add_cps(t["route_id"], [("Start", 0, SAME), ("Middle", 3, NEAR)])
    await db.teach_sessions.update_one({"id": t["id"]}, {"$set": {"status": "finished"}})
    print("builder route:", r["id"], "| teach session:", t["id"], "route:", t["route_id"])


async def cleanup():
    from migrations import delete_routes_cascade
    routes = await db.routes.find({"name": {"$regex": "^(TEMP P19|TEST_P19|TEST_phase19|Check )"}}, {"_id": 0, "id": 1, "name": 1}).to_list(100)
    scan_routes = [s["route_id"] for s in await db.scan_sessions.find({}, {"_id": 0, "route_id": 1}).to_list(100)]
    ids = list({r["id"] for r in routes} | set(scan_routes))
    mems = await db.route_memories.find({"route_id": {"$in": ids}}, {"_id": 0}).to_list(100)
    out = await delete_routes_cascade(ids)
    await db.teach_sessions.delete_many({"route_id": {"$in": ids}})
    await db.scan_sessions.delete_many({})
    await db.route_memories.delete_many({"route_id": {"$in": ids}})
    print("deleted routes:", [r["name"] for r in routes], "+ scan routes", len(scan_routes))
    print("photos unservable:", out["photos_unservable"])
    print("memory objects left:", [m.get(k) for m in mems for k in ("points_path", "colors_path", "json_path") if m.get(k)])


asyncio.run(cleanup() if sys.argv[1:2] == ["cleanup"] else seed())
