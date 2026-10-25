"""AI-drafted progress notes grounded only in a code-built text fact sheet of the attempt log; saved notes are read-only."""
import asyncio
import logging
import os
import re
import uuid
from collections import Counter
from datetime import datetime
from typing import Annotated

from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from pymongo.errors import DuplicateKeyError

from db import db
from models import ProgressNote, now_iso
from review import attempt_review
from workspace import AUTHOR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

NOTE_TIMEOUT_S = 45
FAIL = "Couldn't draft a note. Try again."
HEADINGS = ["Summary", "Checkpoints reached", "Cues (spoken / held back, with main reasons)", "Help requests", "Observations", "Suggested focus for the next session"]
REASON_GROUP = {"duplicate": "Not repeated (already said)", "rate_limited": "Held back by the 3-second limit", "low_confidence": "Not sure enough",
                "known_entity": "Already in the route memory", "pause_already_sent": "Pause message already given", "vision_error": "Vision check failed"}
SYSTEM = (
    "You draft short clinical progress notes for an orientation and mobility practitioner. "
    "Use ONLY the facts in the fact sheet. Do not add anything that is not in it: no diagnoses, no feelings, no causes, no names or numbers that aren't there. "
    "Use the numbers exactly as given in the fact sheet. If something isn't in the fact sheet, write \"Not recorded\". "
    "Write plain text, no markdown. Use exactly these six headings, each alone on its own line, in this order:\n" + "\n".join(HEADINGS) + "\n"
    "Under \"Suggested focus for the next session\" phrase the focus as a suggestion for the practitioner to consider; the practitioner decides."
)
DRAFTS: dict = {}


def mss(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def fact_sheet(review: dict, corrections: list) -> str:
    h, items = review["header"], review["timeline"]
    cps = [i for i in items if i["kind"] == "checkpoint"]
    missed = [i for i in items if i["kind"] == "missed"]
    held = Counter(REASON_GROUP.get((i["raw"] or {}).get("policy", {}).get("suppressed_reason"), "Other") for i in items if i["category"] == "suppressed")
    helps = [mss(i["at"]) for i in items if i["kind"] == "help"]
    msgs = [i for i in items if i["kind"] == "message"]
    pauses = sum(1 for i in items if i["kind"] == "run" and i["text"] == "Paused")
    lines = [
        "FACT SHEET (from the attempt log; counts computed by code)",
        f"Client: {h['client']}",
        f"Route: {h['route']} (route version {h['version']})",
        f"Goal: {h['goal'] or 'Not recorded'}",
        f"Date: {datetime.fromisoformat(h['started_at']).date().isoformat()}",
        f"Elapsed time excluding pauses: {mss(h['elapsed_seconds'])} ({int(round(h['elapsed_seconds']))} seconds)",
        f"Pauses: {pauses}",
        f"Checkpoints reached: {h['checkpoints_reached']} of {h['checkpoints_total']}" + (f" ({'; '.join(i['text'] for i in cps)})" if cps else ""),
        f"Checkpoints missed: {len(missed)}" + (f" ({'; '.join(i['text'] for i in missed)})" if missed else ""),
        f"Cues spoken: {h['cues_spoken']}",
        f"Cues held back: {h['cues_suppressed']}" + (" (" + "; ".join(f"{k}: {v}" for k, v in held.most_common()) + ")" if held else ""),
        f"Routine silences (not counted as held back): {h['routine_hidden']}",
        f"Help requests: {h['help_count']}" + (f" (at {', '.join(helps)})" if helps else ""),
        f"Practitioner messages: {len(msgs)}" + "".join(f"\n- at {mss(m['at'])}: \"{m['text']}\"" for m in msgs),
        f"Corrections made in review: {len(corrections)}" + "".join(f"\n- {c}" for c in corrections),
        "Timeline (minutes:seconds from start):",
    ]
    for i in items:
        line = f"- {mss(i['at'])} {i['label']}" + (" (spoken cue)" if i["category"] == "spoken" and i["label"] != "Spoken cue" else "") + f": {i['text']}"
        if i["category"] == "suppressed" and i.get("would_have_said"):
            line = f"- {mss(i['at'])} Held back (would have said): {i['text']}"
        lines.append(line + (f" [{i['reason']}]" if i.get("reason") else ""))
    return "\n".join(lines)


def headings_ok(text: str) -> bool:
    found = [ln.strip().strip("#*").strip().rstrip(":").strip() for ln in text.splitlines()]
    idx = [found.index(hd) if hd in found else -1 for hd in HEADINGS]
    return all(i >= 0 for i in idx) and idx == sorted(idx)


NUM = re.compile(r"\d+(?:\.\d+)?")


def unknown_numbers(draft: str, sheet: str) -> list:
    known = {float(n) for n in NUM.findall(sheet)}
    return sorted({n for n in NUM.findall(draft) if float(n) not in known})


async def _ask(sheet: str) -> str:
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"note-{uuid.uuid4()}", system_message=SYSTEM).with_model("anthropic", os.environ["NOTE_MODEL"])
    parts = []
    async for ev in chat.stream_message(UserMessage(text=sheet)):
        if isinstance(ev, TextDelta):
            parts.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    return "".join(parts).strip()


async def draft_from_sheet(sheet: str) -> str:
    """Two tries at most; raises if both miss a heading, or on failure/timeout."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + NOTE_TIMEOUT_S
    for _ in range(2):
        text = await asyncio.wait_for(_ask(sheet), max(1.0, deadline - loop.time()))
        if headings_ok(text):
            return text
        logger.warning("Progress note draft missing headings; retrying")
    raise ValueError("headings missing")


async def ended_review(attempt_id: str) -> dict:
    review = await attempt_review(attempt_id)
    if review["header"]["status"] != "ended":
        raise HTTPException(status_code=409, detail="Available after the run ends")
    if await db.progress_notes.find_one({"attempt_id": attempt_id}):
        raise HTTPException(status_code=409, detail="This attempt already has a saved note")
    return review


async def correction_lines(attempt_id: str) -> list:
    out = []
    for c in await db.corrections.find({"attempt_id": attempt_id}, {"_id": 0}).sort("created_at", 1).to_list(100):
        b, a = c.get("before") or {}, c.get("after") or {}
        if c["action"] == "dismiss":
            out.append(f"{b.get('label')} dismissed (no change to the route memory)")
        else:
            out.append(f"{a.get('label')} ({a.get('side')}) confirmed, saved as route version {c.get('new_route_version')}")
    return out


@router.post("/attempts/{attempt_id}/note/draft")
async def draft_note(attempt_id: str):
    review = await ended_review(attempt_id)
    sheet = fact_sheet(review, await correction_lines(attempt_id))
    model = os.environ["NOTE_MODEL"]
    try:
        text = await draft_from_sheet(sheet)
    except Exception as exc:
        logger.warning("Progress note draft failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail=FAIL)
    unknown = unknown_numbers(text, sheet)
    if unknown:
        logger.warning("Progress note draft has numbers not in the fact sheet: %s", unknown)
    draft_id = str(uuid.uuid4())
    DRAFTS[draft_id] = {"attempt_id": attempt_id, "text": text, "model": model}
    return {"draft_id": draft_id, "draft": text, "model": model, "numbers_ok": not unknown, "unknown_numbers": unknown}


class NoteIn(BaseModel):
    draft_id: str
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


def note_out(n: dict) -> dict:
    return {k: n.get(k) for k in ("id", "attempt_id", "client_id", "text", "ai_draft", "model", "author", "approved_at")}


@router.post("/attempts/{attempt_id}/note", status_code=201)
async def save_note(attempt_id: str, body: NoteIn):
    review = await ended_review(attempt_id)
    draft = DRAFTS.get(body.draft_id)
    if not draft or draft["attempt_id"] != attempt_id:
        raise HTTPException(status_code=422, detail="This draft has expired. Draft the note again.")
    ex = await db.exercises.find_one({"id": (await db.attempts.find_one({"id": attempt_id}))["exercise_id"]}, {"_id": 0, "client_id": 1})
    note = ProgressNote(attempt_id=attempt_id, client_id=ex["client_id"], text=body.text, ai_draft=draft["text"], model=draft["model"], author=AUTHOR, approved_at=now_iso(),
                        route_name=review["header"]["route"], route_version=review["header"]["version"], attempt_date=review["header"]["started_at"], client_name=review["header"]["client"])
    try:
        await db.progress_notes.insert_one(note.to_mongo())
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="This attempt already has a saved note")
    DRAFTS.pop(body.draft_id, None)
    return note_out(note.to_mongo())


def listed(n: dict) -> dict:
    return {**note_out(n), **{k: n.get(k) for k in ("route_name", "route_version", "attempt_date", "client_name")}}


@router.get("/attempts/{attempt_id}/note")
async def get_note(attempt_id: str):
    n = await db.progress_notes.find_one({"attempt_id": attempt_id}, {"_id": 0})
    return {"note": listed(n) if n else None}


@router.get("/clients/{client_id}/notes")
async def client_notes(client_id: str):
    if not await db.clients.find_one({"id": client_id}):
        raise HTTPException(status_code=404, detail="Client not found")
    return [listed(n) for n in await db.progress_notes.find({"client_id": client_id}, {"_id": 0}).sort("approved_at", -1).to_list(500)]


@router.get("/notes/{note_id}")
async def one_note(note_id: str):
    n = await db.progress_notes.find_one({"id": note_id}, {"_id": 0})
    if not n:
        raise HTTPException(status_code=404, detail="Note not found")
    return listed(n)
