"""Phase 12 checks: progress notes + machine view + memory endpoint.
  python3 note_check.py drafts     two real drafts (structure, numbers check, fact sheet contents) - nothing saved
  python3 note_check.py fail       forced AI failure (bad model, in-process) -> message, nothing saved
  python3 note_check.py save       draft + save on the 3D demo, 409, empty, no modify routes (note kept until `cleanup`)
  python3 note_check.py memory     memory endpoint v1/v2/latest/404s + schema check on both demo routes
  python3 note_check.py replan     (CUE_TEST_HOOK=1) temporary copy route: run with depth, confirm a left object -> REPLAN_RIGHT; run API leak check; deletes it
  python3 note_check.py cleanup    delete check notes
"""
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
UA = {"User-Agent": "between-visit-check/1.0"}
DEMO = json.loads(Path("/app/tests/.review_demo.json").read_text())
HEADINGS = ["Summary", "Checkpoints reached", "Cues (spoken / held back, with main reasons)", "Help requests", "Observations", "Suggested focus for the next session"]


def get(p, **kw):
    return requests.get(f"{API}{p}", headers=UA, timeout=90, **kw)


def post(p, **kw):
    return requests.post(f"{API}{p}", headers={**UA, **kw.pop("headers", {})}, timeout=90, **kw)


def drafts():
    import notes
    from review import attempt_review
    for name in ("3d", "2d"):
        aid = DEMO[name]["attempt_id"]
        import db as dbmod
        from motor.motor_asyncio import AsyncIOMotorClient

        async def build():
            dbmod.db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
            for mod in (notes, sys.modules["review"], sys.modules["corrections"], sys.modules["machine"]):
                mod.db = dbmod.db
            rv = await attempt_review(aid)
            return rv, notes.fact_sheet(rv, await notes.correction_lines(aid))
        rv, sheet = asyncio.run(build())
        leaks = [w for w in ("photo", "/api/", "jpeg", "base64", "depth_", " points", "key", "pos_x", "trail") if w in sheet.lower()]
        t = time.time(); r = post(f"/attempts/{aid}/note/draft"); s = time.time() - t
        d = r.json()
        h = rv["header"]
        text = d["draft"]
        print(f"== {name.upper()} draft {r.status_code} in {s:.1f} s | model {d['model']} | headings in order: {notes.headings_ok(text)} | numbers_ok {d['numbers_ok']} {d['unknown_numbers']}")
        print(f"   fact sheet {len(sheet)} chars, excluded-data words found: {leaks}")
        need = [f"{h['checkpoints_reached']} of {h['checkpoints_total']}", str(h["cues_spoken"]), str(h["cues_suppressed"]), str(h["help_count"])]
        print("   header numbers present in draft:", {n: n in text for n in need}, "| 'suggest' wording:", bool(re.search(r"suggest|consider|could|may", text.split("Suggested focus for the next session")[-1], re.I)))
        print("   ---- excerpt ----\n" + "\n".join("   " + ln for ln in text.splitlines()[:16]))


def fail():
    import notes
    os.environ["NOTE_MODEL"] = "claude-does-not-exist"
    from fastapi import HTTPException
    try:
        asyncio.run(notes.draft_note(DEMO["2d"]["attempt_id"]))
        print("FAIL path: no error raised")
    except HTTPException as e:
        print("forced AI failure ->", e.status_code, e.detail)
    print("notes saved for the attempt:", get(f"/attempts/{DEMO['2d']['attempt_id']}/note").json())


def save():
    aid = DEMO["3d"]["attempt_id"]
    d = post(f"/attempts/{aid}/note/draft").json()
    print("empty text:", post(f"/attempts/{aid}/note", json={"draft_id": d["draft_id"], "text": "   "}).status_code)
    edited = d["draft"].replace("Summary", "Summary", 1) + "\n\n(Edited by J. Rivera before saving.)"
    r = post(f"/attempts/{aid}/note", json={"draft_id": d["draft_id"], "text": edited})
    n = r.json()
    print("save:", r.status_code, {k: n[k] for k in ("author", "approved_at", "model")}, "| ai_draft kept separately:", n["ai_draft"] == d["draft"] and n["text"] != n["ai_draft"])
    d2 = post(f"/attempts/{aid}/note/draft")
    print("second draft after save:", d2.status_code, d2.json().get("detail"))
    print("second save:", post(f"/attempts/{aid}/note", json={"draft_id": d["draft_id"], "text": "again"}).status_code)
    before = get(f"/notes/{n['id']}").json()
    mods = {m: getattr(requests, m)(f"{API}/notes/{n['id']}", headers=UA, json={"text": "x"}).status_code for m in ("put", "patch", "delete")}
    mods.update({f"{m} attempt note": getattr(requests, m)(f"{API}/attempts/{aid}/note", headers=UA, json={"text": "x"}).status_code for m in ("put", "patch", "delete")})
    print("Q-57 modify attempts:", mods, "| unchanged:", get(f"/notes/{n['id']}").json() == before)
    cid = n["client_id"]
    print("client notes:", [(x["route_name"], x["route_version"], x["author"]) for x in get(f"/clients/{cid}/notes").json()])
    Path("/app/tests/.note_check.json").write_text(json.dumps({"note_id": n["id"]}))


def schema_ok(m):
    pos_ok = lambda p: p is None or (set(p) == {"x", "y", "z", "units", "origin"} and p["units"] == "m" and p["origin"] == "route_start")
    top = set(m) == {"source", "authoritative", "route_id", "version", "checkpoints", "entities"} and m["authoritative"] is False and m["source"] == "BetweenVisit route memory"
    cps = all(set(c) == {"order", "name", "landmark_text", "position"} and pos_ok(c["position"]) for c in m["checkpoints"])
    ents = all(set(e) == {"type", "authoritative", "source", "route_id", "version", "entity", "advice"} and e["type"] in ("REPLAN_LEFT", "REPLAN_RIGHT") and e["authoritative"] is False
               and set(e["entity"]) == {"label", "side", "segment", "position", "verified_by", "verified_at"} and pos_ok(e["entity"]["position"]) for e in m["entities"])
    raw = json.dumps(m).lower()
    leaks = [w for w in ("photo", "/api/", '"points"', "planes", "trail", "key", "hash", "frame", "data:image") if w in raw]
    return top and cps and ents and not leaks, leaks


def memory():
    from db import db
    bad = 0
    for name in ("3d", "2d"):
        rid = DEMO[name]["route_id"]
        for q in ("", "?version=1", "?version=2"):
            r = get(f"/routes/{rid}/memory{q}")
            if r.status_code == 404:
                print(f"{name}{q or ' latest'}: 404 (no such version)"); continue
            m = r.json(); ok, leaks = schema_ok(m); bad += not ok
            print(f"{name}{q or ' latest'}: v{m['version']} schema ok {ok} leaks {leaks} | checkpoint positions {[c['position'] and (c['position']['x'], c['position']['z']) for c in m['checkpoints']]} | entities {[(e['type'], e['entity']['label'], e['entity']['segment'], e['entity']['position'], e['advice']) for e in m['entities']]}")
    async def test_id():
        return (await db.routes.find_one({"is_test": True}, {"_id": 0, "id": 1}))["id"]
    test_route = asyncio.run(test_id())
    print("404s: unknown", get("/routes/nope/memory").status_code, "| v99", get(f"/routes/{DEMO['3d']['route_id']}/memory?version=99").status_code, "| hidden test route", get(f"/routes/{test_route}/memory").status_code)
    print("Q-58 failing responses:", bad)
    h = get(f"/routes/{DEMO['3d']['route_id']}/history").json()
    rv = get(f"/attempts/{DEMO['3d']['attempt_id']}/review").json()
    item = next(i for i in rv["timeline"] if i.get("machine"))
    print("machine view (history) == (review item) == (memory endpoint):", h["known_entities"][0]["machine"] == item["machine"] == get(f"/routes/{DEMO['3d']['route_id']}/memory").json()["entities"][0])
    print(json.dumps(item["machine"], indent=1))


def replan():
    import memory_check as mc
    from db import db

    async def go():
        rid, cps = await mc.copy_route(DEMO["3d"]["route_id"], "Note check copy (synthetic)")
        made = mc.rd.assign(rid, "standard")
        await mc.simulate(made, cps, mc.mover_3d(made["attempt"], made["key"], (0.0, 0.0), True))
        aid = made["attempt"]["id"]
        left = next(i for i in mc.entity_items(aid) if i["entity"]["side"] == "left")
        print("confirm left object:", left["text"], post(f"/attempt-events/{left['id']}/correction", json={"action": "confirm"}).status_code)
        m = get(f"/routes/{rid}/memory").json()
        print("JRN-172:", json.dumps(m["entities"][0]), "| schema ok:", schema_ok(m))
        k = {**UA, "X-Stream-Key": made["key"]}
        pub = requests.get(f"{API}/run/{aid}", headers=k).text + requests.get(f"{API}/run/{aid}/cues", headers=k).text
        print("JRN-176 run API mentions note/machine/REPLAN/authoritative/route memory:", [w for w in ("note", "machine", "REPLAN", "authoritative", "route memory", "ai_draft") if w in pub])
        run = post(f"/exercises/{made['exercise']['id']}/attempts").json()
        post(f"/run/{run['attempt']['id']}/start", headers={"X-Stream-Key": run["key"]})
        print("draft on a running attempt:", post(f"/attempts/{run['attempt']['id']}/note/draft").json())
        Path("/app/tests/.note_check.json").write_text(json.dumps({"route_id": rid, "running_attempt": run["attempt"]["id"]}))
    asyncio.run(go())


def replan_cleanup():
    import memory_check as mc
    from db import db
    rid = json.loads(Path("/app/tests/.note_check.json").read_text())["route_id"]

    async def go():
        ex = await db.exercises.distinct("id", {"route_id": rid})
        atts = await db.attempts.distinct("id", {"exercise_id": {"$in": ex}})
        evs = await db.attempt_events.distinct("id", {"attempt_id": {"$in": atts}})
        print("cleanup: corrections", (await db.corrections.delete_many({"attempt_event_id": {"$in": evs}})).deleted_count, "| notes", (await db.progress_notes.delete_many({"attempt_id": {"$in": atts}})).deleted_count, "| route", await mc.delete_routes_cascade([rid]))
    asyncio.run(go())


def cleanup():
    from db import db
    print("notes deleted:", asyncio.run(db.progress_notes.delete_many({})).deleted_count)
    Path("/app/tests/.note_check.json").unlink(missing_ok=True)


if __name__ == "__main__":
    {"drafts": drafts, "fail": fail, "save": save, "memory": memory, "replan": replan, "replan-cleanup": replan_cleanup, "cleanup": cleanup}[sys.argv[1]]()
