# Phase 12 Requirements: Progress Note + Machine View
Version: phase-12

Goal: the practitioner gets an AI-drafted progress note grounded only in the attempt log, edits and approves it (read-only after), and can print or copy it. Confirmed route memory is also available as read-only machine JSON per entity and through a memory endpoint. See ../overview.md. Phases 1–11 must keep working. Check data is deleted afterwards (demo data from Phases 10–11 is kept).

## Progress note
- REQ-386 [state] While the attempt is ended and has no saved note, the review page shall show "Draft progress note".
- REQ-387 [state] While the attempt isn't ended, the button shall be disabled with "Available after the run ends".
- REQ-388 [event] When "Draft progress note" is pressed, the system shall build a text fact sheet from the attempt log only: events, cues (spoken/held back + reasons), checkpoints (n of N, names), help requests, practitioner messages, corrections, elapsed time. Counts are computed by code.
- REQ-389 [always] The system shall never send images, frames, photos, depth, points or keys to the note model.
- REQ-390 [always] The system shall call Claude Sonnet 5.5 via the Emergent LLM key, the model in one config setting (e.g. NOTE_MODEL).
- REQ-391 [always] The prompt shall require exactly these sections in order: Summary; Checkpoints reached; Cues (spoken / held back, with main reasons); Help requests; Observations; Suggested focus for the next session.
- REQ-392 [always] The prompt shall forbid anything not in the fact sheet, require the code-computed numbers, and require "Not recorded" for missing information.
- REQ-393 [always] The prompt shall frame the next-session focus as a suggestion for the practitioner to decide.
- REQ-394 [unwanted] If the draft lacks any of the six section headings, then the system shall retry once, then show "Couldn't draft a note. Try again."
- REQ-395 [unwanted] If the AI call fails or times out (~45 s), then the system shall show "Couldn't draft a note. Try again." with nothing saved.
- REQ-396 [always] The draft shall be shown in an editable labelled text area under the label "Draft written by AI from the attempt log. Review before saving."
- REQ-397 [event] When "Approve and save" is pressed, the system shall save the note (attempt_id, client_id, text, original AI draft, author "J. Rivera (synthetic)", approved_at, model).
- REQ-398 [unwanted] If the text is empty, then the system shall block saving with a message.
- REQ-399 [unwanted] If the attempt already has a saved note, then the system shall reject another (409).
- REQ-400 [always] Saved notes shall be read-only; no edit or delete endpoint.
- REQ-401 [always] Saved notes shall be stored in a new progress_notes collection. (interpreted)
- REQ-402 [state] While a note is saved, the review page shall show it read-only with author and time, plus a collapsed "Original AI draft" section.
- REQ-403 [always] The client page shall list that client's saved notes (date, route + version, author) with Copy and Print buttons.
- REQ-404 [event] When Copy is pressed, the system shall copy the note text (with a header line of client, date, route) to the clipboard and announce "Copied".
- REQ-405 [event] When Print is pressed, the system shall open a print view: client display name, date, route + version, note text, author + time, and the footer disclaimer; no nav.
- REQ-406 [always] Notes shall never appear on the client run page or its API.

## Machine view
- REQ-407 [always] Each confirmed entity in the review page and version history shall have a "Machine view" toggle (collapsed by default) showing read-only JSON.
- REQ-408 [always] The JSON shall be {"type", "authoritative": false, "source": "BetweenVisit route memory", "route_id", "version", "entity": {"label", "side", "segment": {"from","to"}, "position", "verified_by", "verified_at"}, "advice"}.
- REQ-409 [always] type shall be "REPLAN_LEFT" for side right or ahead, and "REPLAN_RIGHT" for left.
- REQ-410 [always] advice: right → "Reported <label> right of the path; keep left."; ahead → "Reported <label> ahead on the path; keep left."; left → "Reported <label> left of the path; keep right." (interpreted for ahead/left)
- REQ-411 [always] position shall be {"x","y","z","units":"m","origin":"route_start"} (start-relative; y null when unknown) or null. (interpreted)
- REQ-412 [always] version shall be the route version being viewed (the version that holds the entity).
- REQ-413 [always] The toggle shall offer a "Copy JSON" button. (interpreted)

## Memory endpoint
- REQ-414 [event] When GET /api/routes/{id}/memory?version=N is called, the system shall return {"source": "BetweenVisit route memory", "authoritative": false, "route_id", "version", "checkpoints": [...], "entities": [machine-view objects]}.
- REQ-415 [always] Each checkpoint shall have order, name, landmark_text, and position {"x","y","z","units":"m","origin":"route_start"} when the route was taught by walking (start-relative to the teach start), else null.
- REQ-416 [always] The response shall contain no photo links, points, planes, trail, frames, keys or hashes.
- REQ-417 [state] While version is omitted, the endpoint shall return the latest version.
- REQ-418 [unwanted] If the route or version is unknown, or the route is the hidden test route, then the endpoint shall return 404.
- REQ-419 [always] Entities removed in or before version N shall not appear for version N.

## Quality requirements
```
Q-54 Tag: Note.Faithfulness
     Scale: claims in the draft not supported by the fact sheet (numbers, events, names)
     Meter: human + a code check that every number in the draft appears in the fact sheet (warn if not)
     Must: 0   Plan: 0
Q-55 Tag: Note.Structure
     Scale: drafts missing a required section
     Meter: 3 drafts on the demo attempts
     Must: 0   Plan: 0
Q-56 Tag: Note.Latency
     Scale: seconds from button to draft shown
     Meter: 3 trials
     Must: 45   Plan: 15 (estimate)
Q-57 Tag: Note.Integrity
     Scale: saved notes changed after approval
     Meter: API attempts to modify
     Must: 0   Plan: 0
Q-58 Tag: Memory.Contract
     Scale: memory responses failing the JSON shape / leaking excluded data
     Meter: schema check on both demo routes, v1 and v2
     Must: 0   Plan: 0
```
