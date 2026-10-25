# Requirements: Between Visit

## Core Value
Orientation-and-mobility (O&M) practices assign, monitor and review between-session route exercises for blind and low-vision clients. This step is only the skeleton and data model.

## Personas & Roles
- Practitioner (O&M specialist): sees the practice and its clients. No login yet.
- Client (synthetic only): not a UI user in this phase.

## Features
| id | feature | persona | phase |
|---|---|---|---|
| F-1 | All 10 MongoDB collections with id + created_at on every one, and indexes on foreign keys | system | 1 |
| F-2 | Seed on startup only if empty: practice, practitioner, 2 synthetic clients | system | 1 |
| F-3 | GET /api/health returns {"ok": true} | system | 1 |
| F-4 | GET list endpoints for practices, practitioners, clients | practitioner | 1 |
| F-5 | Home page shows the practice, the practitioner and both clients (names only) | practitioner | 1 |
| F-6 | Footer on every page with the exact disclaimer text | all | 1 |
| F-7 | Accessibility: large text, high contrast, keyboard-friendly, ARIA labels | all | 1 |
| F-9 | Move stream_id + key from exercises to attempts (one per attempt); seed test attempt "att-test" for Client A | system | 2 |
| F-10 | WebSocket device ingest /api/ws/ingest/{stream_id}?key= (frames counted then discarded, motion pairing, guide push, reconnect takeover) | device | 2 |
| F-11 | Phone fallback POST /api/attempts/{id}/frame | device | 2 |
| F-12 | /device-test page: server URL, stream ID + key with copy, Live status, counters, send test cue | practitioner | 2 |
| F-13 | Top navigation: Clients, Routes, Device test | practitioner | 3 |
| F-14 | Clients list + read-only client page (name, notes) | practitioner | 3 |
| F-15 | Routes list (name, # checkpoints, current version) + "New route" | practitioner | 3 |
| F-16 | Phone-friendly route builder: name, ordered checkpoints (add/remove/up/down), photo (camera or upload, resized ~1280px, object storage), landmark text | practitioner | 3 |
| F-17 | Claude Sonnet 5.5 vision landmark suggestion (≤25 words, "Suggested by AI"; person → retake, photo discarded) | practitioner | 3 |
| F-18 | Per-checkpoint Approve; "Save route" only when all are approved → route_version N+1 snapshot | practitioner | 3 |
| F-19 | Cleanup: delete the 2 check routes and their photos; hide the test route from Routes | system | 4 |
| F-20 | "Assign exercise" on saved routes: client, goal, cue style, silence rules, stop rule → exercise pinned to version + first attempt | practitioner | 4 |
| F-21 | One-time confirmation: run link (/run/{id}#key=…), stream ID, key, copy buttons | practitioner | 4 |
| F-22 | Client page: exercises with attempts, plus "New attempt" | practitioner | 4 |
| F-23 | /run/{attempt id} placeholder: goal, stream ID, key from the link | client | 4 |
| F-24 | Cleanup of the Reception route + draft and their exercises/attempts; checks always delete their own data | system | 5 |
| F-25 | Client run page: VoiceOver-friendly controls Start/Pause/Resume/Repeat cue/Request help/End, summary, stream ID + key, elapsed/heading/steps, assertive caption | client | 5 |
| F-26 | Attempt status + attempt_events logging (start, pause, resume, end, help, guide) | system | 5 |
| F-27 | Help alert: red "Help requested HH:MM" on the client page, auto-refresh 5 s | practitioner | 5 |
| F-28 | "Message client" box on running/paused attempts → guide cue to phone + GlassCam | practitioner | 5 |
| F-29 | Phone cue polling 1 s, speechSynthesis when GlassCam isn't live, "Speak cues aloud" toggle | client | 5 |
| F-30 | Phone camera fallback (1 JPEG/s with heading + steps), Wake Lock | client | 5 |
| F-31 | Cleanup: the 2 blank-named routes + the empty checkpoint on the hidden test route | system | 6 |
| F-32 | Vision loop per running attempt: newest frame only, ≤1/s, skip while busy, Claude Haiku 4.5 (one config setting), route memory as text, JSON result | system | 6 |
| F-33 | Log "vision" / "vision_error" attempt_events; 8 s timeout; stop after 30 min of running | system | 6 |
| F-34 | GET /api/attempts/{id}/events (newest first) | practitioner | 6 |
| F-35 | "DPT1" LiDAR depth frames on the ingest socket: parse, validate, never to vision/never stored | device | 7 |
| F-36 | {"type":"phone"} lines: newest ar_tracking, ar_pose, heading_deg, has_lidar per stream | device | 7 |
| F-37 | Depth↔phone pairing ±60 ms; left/centre/right median depth; added to vision events and the Claude prompt | system | 7 |
| F-38 | /device-test shows pose, depth L/C/R, depth-frame count | practitioner | 7 |
| F-39 | "Teach by walking": teach session (own stream ID + key, copy buttons), live panel | practitioner | 8 |
| F-40 | Teach-only 3D mapping: depth → world points (5 cm voxels, ≤200k), ar_planes kept, trail every 0.25 m | system | 8 |
| F-41 | Auto-proposed checkpoints (start, end, >45° turns) with person check + Sonnet landmark; other frames discarded | system | 8 |
| F-42 | Review page: three.js 3D view + accessible checkpoint list; Save → v1 with 3D memory | practitioner | 8 |
| F-43 | Client runs store a trail point every 0.25 m (practitioner-only) | system | 8 |
| F-44 | Relevance policy: deterministic backend rules turn each vision event into one "cue" event (spoken or suppressed with a reason); spoken cues go through the existing cue path | client | 9 |
| F-45 | Fix: no "no frames" pause until the first frame or 15 s after Start | client | 10 |
| F-46 | Attempt review page: header stats, filterable timeline with plain-word reasons, 3D/2D path with linked cue dots, two demo attempts | practitioner | 10 |
| F-47 | Fixes: "On route." never counts/blocks; held-back cues retried; vision-failure wording | client | 11 |
| F-48 | Corrections on review items: Confirm / Edit / Dismiss → corrections log; Confirm → next route version with a known entity | practitioner | 11 |
| F-49 | Version history (route + review pages), "Remove from memory" → next version; attempts carry their own version (new = latest) | practitioner | 11 |
| F-51 | AI progress note (Claude Sonnet 5.5, from the attempt log only): draft → edit → approve and save; listed on the client page with Copy/Print | practitioner | 12 |
| F-53 | Demo recording (opt-in checkbox; analysed frames + pose + depth; double person check; "Recording" badge; run page notice) | practitioner / team | 13 |
| F-54 | Replay a recording through the live pipeline on v1 or latest (temperature 0) → new replay attempt | practitioner | 13 |
| F-55 | Replay screen (frame, large caption, voice + mute, checkpoint, counts, live path; 1920×1080 with no scroll) + "Try the demo" on home (≤3 public at once, 24 h auto-delete) | judges / public | 13 |
| F-56 | Synthetic fallback recording (12 AI-generated frames, chair between cp 1–2), labelled "Synthetic demo (AI-generated images)" | system | 13 |

## Phases
- Phase 1: Skeleton + data model + seed + read endpoints + home page → F-1..F-7. [requirement](phase1/requirement.md) · [journeys](phase1/journeys.md)
- Phase 2: Device ingest, no vision → F-9..F-12. [requirement](phase2/requirement.md) · [journeys](phase2/journeys.md)
- Phase 3: Practitioner workspace + route builder → F-13..F-18. [requirement](phase3/requirement.md) · [journeys](phase3/journeys.md)
- Phase 4: Exercise builder + assignment → F-19..F-23. [requirement](phase4/requirement.md) · [journeys](phase4/journeys.md)
- Phase 5: Client run page → F-24..F-30. [requirement](phase5/requirement.md) · [journeys](phase5/journeys.md)
- Phase 6: Vision analysis (no speaking) → F-31..F-34. [requirement](phase6/requirement.md) · [journeys](phase6/journeys.md)
- Phase 7: Phone sensors from GlassCam (LiDAR depth + AR pose) → F-35..F-38. [requirement](phase7/requirement.md) · [journeys](phase7/journeys.md)
- Phase 8: Teach a route by walking → F-39..F-43. [requirement](phase8/requirement.md) · [journeys](phase8/journeys.md)
- Phase 9: Relevance policy (spoken cues, no new UI) → F-44. [requirement](phase9/requirement.md) · [journeys](phase9/journeys.md)
- Phase 10: Start-grace fix + attempt review → F-45..F-46. [requirement](phase10/requirement.md) · [journeys](phase10/journeys.md)
- Phase 11: Fixes + corrections and route memory versions → F-47..F-50. [requirement](phase11/requirement.md) · [journeys](phase11/journeys.md)
- Phase 12: Progress note + machine view → F-51..F-52. [requirement](phase12/requirement.md) · [journeys](phase12/journeys.md)
- Phase 13: Demo recording + replay → F-53..F-56. [requirement](phase13/requirement.md) · [journeys](phase13/journeys.md)
- Phase 14: Polish (landing, research, demo renames, nav, accessibility, copy audit), no new features. [requirement](phase14/requirement.md) · [journeys](phase14/journeys.md)
- Next: the deferred checkpoint-2 match check after the first real teach walk.
- Later phases: to be defined with the user.

## UI/UX Rules
- Large text (base ≥18px), high contrast (WCAG AA, aim for AAA), visible focus rings, keyboard reachable, semantic landmarks + ARIA labels.
- Footer text exactly: "Experimental practice tool used under the practitioner's direction. It doesn't replace the cane, the dog guide or the specialist, and it isn't a safety device."
- Error state copy: "Couldn't load practice data".

## Integrations
None in Phase 1. No auth.
- Phase 2: none external.
- Phase 3: Claude Sonnet 5.5 (vision) via the Emergent LLM key (emergentintegrations), for landmark suggestions. Emergent Object Storage for checkpoint photos.
- Phase 6: Claude Haiku 4.5 vision via the Emergent LLM key for live frame analysis (model in a single config setting). Frames are sent to Anthropic in memory only, never stored.

## Edge Cases
- Synthetic people only: clients.synthetic must be true; the model rejects false.
- Never store frames from client runs. Only checkpoint photos of empty spaces (photo_url) are stored.
- (Phase 2) stream_id + key live on attempts, not exercises. The key is a private access code; it's never returned by list endpoints or written to logs. It's stored hashed. Only the seeded test attempt's key is shown, on /device-test. Later, the practitioner sees a new attempt's key exactly once, when it's created.
- Frames are never stored: count, last time, last size, then discard.
- (Phase 13) The ONLY exception: runs explicitly ticked "Record this run as a demo (empty space, team only)" store the frames that were analysed (~1/s) with time, pose and depth L/C/R, and only if BOTH the live vision result and a Sonnet person check find no person (fail closed). Storage can't delete, so a stored frame can only be made unservable. Replay attempts are public demo data: their frames, pose path and cues may be shown on the public replay screen. Everything else keeps the original rules.
- (Phase 4) A new attempt's key is shown once in the assignment/new-attempt confirmation. It travels only in the run link's URL fragment (/run/{id}#key=…), which never reaches the server. The server keeps only the hash. If the key is lost, make a new attempt.
- Seeding is idempotent: restarting never creates duplicates.
- Backend down or empty data → the home page shows "Couldn't load practice data".

## Seed Data
- Rule (from Phase 5): any data created for checks is deleted afterwards. Object storage can't delete files (405), so check photos must be made unservable and reported.
- Practice: "Bay Mobility Practice"
- Practitioner: "J. Rivera (synthetic)", role "O&M specialist"
- Clients: "Client A (synthetic)", "Client B (synthetic)", synthetic: true
- No other collections are seeded.
