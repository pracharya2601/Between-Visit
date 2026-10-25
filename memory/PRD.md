# Between Visit — PRD

## Original problem statement
Build Phase 1 (skeleton + data model) of "Between Visit": FastAPI + MongoDB + React. See /app/memory/product/overview.md, phase1/requirement.md (REQ-1..19, Q-1..5), phase1/journeys.md (JRN-1..12).

## Personas
- Practitioner (O&M specialist), no login yet. Clients are synthetic only.

## Architecture
- backend/models.py: Pydantic models for 10 collections (BaseDocument: id uuid + created_at ISO UTC); ExercisePublic excludes `key`; COLLECTIONS + FOREIGN_KEYS maps.
- backend/server.py: lifespan → indexes (unique id + FK indexes) + idempotent seed; GET /api/health, /api/practices, /api/practitioners, /api/clients; OpenAPI at /api/openapi.json.
- frontend: Layout (skip link, header/main/footer landmarks, disclaimer footer), Home page (aria-live status, error copy), AAA light theme, 20px base, Atkinson Hyperlegible font, reduced-motion support.

## Implemented (2026-10-24)
- Phase 1, F-1..F-7. Sanity checks done: 4 endpoints curled, restart showed no duplicate seed, validation rejections checked, home page screenshot taken.

## Phase 2 implemented (2026-10-24): device ingest, no vision
- stream_id (unique) + key_hash (sha256, hmac.compare_digest) moved to attempts; exercises lost them. Seeded "Test route (synthetic)", one exercise for Client A, attempt "att-test"; plain test key only in `test_config`, read by GET /api/device-test/config.
- backend/ingest.py: WS /api/ws/ingest/{stream_id}?key= (1008 on bad key/stream, {"viewers":0}, ≤1 MB frames counted + discarded, >1 MB dropped, motion pairing, takeover), POST /api/attempts/{id}/frame (phone fallback), GET /api/attempts/{id}/status, POST /api/attempts/{id}/cue (409 "Not connected", 422 on length). Log filter on uvicorn.access/error drops ingest paths and "key=".
- Ingest counters are in memory and reset when the backend restarts.
- Frontend /device-test page (copy fields, 1s status poll, cue form), linked from home.
- Verified over the public wss:// URL with tests/wss_ingest_check.py.

## Phase 3 implemented (2026-10-24): practitioner workspace + route builder
- Top nav (Clients, Routes, Device test; NavLink aria-current). Clients list + read-only client page ("Client not found"). Routes list (count, version / "Not saved yet") + New route.
- backend/workspace.py: route/checkpoint CRUD (add/remove/move/rename/patch), approve, photo pipeline, photo proxy GET /api/photos/{id}, save → immutable route_version (unique route_id+version), versions list.
- backend/vision.py: Pillow resize to 1280px wide (no upscale), EXIF/GPS stripped; Claude Sonnet 5.5 (`claude-sonnet-5-5`, Emergent LLM key) with 30s timeout; person → retake, photo discarded; ≤25 words.
- backend/storage.py: Emergent Object Storage; `photos` collection keeps storage_path (never exposed).
- Unsaved routes reset to current_version 0 on startup.
- Frontend: Clients, ClientDetail, Routes, RouteBuilder, CheckpointCard, PhotoPicker; drafts saved (debounced 500 ms).
- Checks: tests/route_builder_check.py (real Claude calls, resize, v1/v2), tests/wss_ingest_check.py re-run OK.

## Phase 4 implemented (2026-10-24): exercise builder + assignment
- Cleanup (backend/migrations.py, runs once, recorded in `migrations`): deleted "Check route" + "Library entrance" routes, 6 checkpoints, 2 route_versions. Object storage has NO delete (DELETE → 405), so the 3 photos are flagged is_deleted and the proxy returns 404; the bytes remain in storage.
- Test route flagged is_test: hidden from Routes, 404 in the workspace API, not assignable. att-test unchanged.
- Exercises: route_version (pinned) + silence_rules {stay_silent_on_route, no_repeat, note}. Attempts: "att-" + 4 chars (unique, retried), key hash only, status not_started.
- backend/exercises.py: POST /api/routes/{id}/exercises (exercise + first attempt; the exercise is deleted if the attempt fails, since there are no Mongo transactions on a standalone server), POST /api/exercises/{id}/attempts, GET /api/clients/{id}/exercises, GET /api/run/{id}, POST /api/run/{id}/verify (key in body).
- Frontend: AssignExercise page + AssignForm, OneTimeConfirmation (run link with #key, stream ID, key, copy, shown-once warning), ExerciseList on client page with New attempt, /run/:id page without nav.
- Demo data: "Reception route (synthetic)" (v2, exercise pinned to v1 for Client A, 2 attempts), "Unsaved draft (synthetic)".

## Phase 5 implemented (2026-10-24): client run page
- Cleanup migration phase5-cleanup removed Reception route + Unsaved draft (2 routes, 1 checkpoint, 2 versions, 2 exercises, 3 attempts); photo 07adbf27-d646-48db-b321-6fbe27c5bed0 is now unservable (404; storage has no delete).
- backend/run.py: X-Stream-Key-protected run API (GET info, cues polling with seq cursor, ack, help, repeat, start/pause/resume/end with strict 409 transitions), practitioner POST /api/attempts/{id}/message. Every action is logged as an attempt_event (seq, t ISO UTC). Attempts track active_seconds/running_since, so elapsed time excludes pauses.
- ingest.py: glasses vs phone frame counters, push_guide helper.
- migrations.py: generic delete_routes_cascade + cleanup_once.
- Frontend: pages/ClientRun.jsx + components/run/* (RunSession, RunControls, EndConfirm, RunMetrics, RunSummary, PhoneCamera), hooks useMotion/useWakeLock/usePhoneCamera, lib/speech.js; client page auto-refresh 5 s with AttemptRow (red help alert, Message client).
- Check scripts: tests/run_check_data.py (setup/cleanup), tests/run_api_check.py. Check data deleted after use.

## Phase 6 implemented (2026-10-24): vision analysis (no speaking)
- phase6-cleanup migration: deleted the 2 blank routes (by id only) and the empty checkpoint on the hidden test route.
- New route now needs a name: POST /api/routes {name} and PATCH both reject blank names; the Routes page has a name field + "Create route".
- backend/vision_worker.py: one frame slot per attempt (newest wins, frames during a call discarded, no queue), ≥1 s between call starts, only while running, 30-min running cap → one "vision_stopped". Model from VISION_MODEL in backend/.env (claude-haiku-4-5-20251001), 8 s timeout. Pydantic validation, checkpoint name check, person label stripping. Events: vision / vision_error {reason, latency_ms, model}.
- ingest.py offers every accepted glasses/phone frame to the worker; counters unchanged.
- GET /api/attempts/{id}/events (newest first, 404 unknown).
- The first model call after a backend start stalls the event loop up to about 1.2 s (library warm-up); after that it's about 20 ms.
- Check script: tests/vision_check.py (with tests/run_check_data.py setup/cleanup).
- DEFERRED: REQ-206 checkpoint-2 check, to a later step where the route is created automatically from a GlassCam walk. Keep tests/vision_check.py for it. Phase 6 closed.

## Phase 7 implemented (2026-10-24): phone sensors from GlassCam (depth + pose)
- backend/sensors.py: DPT1 depth parsing (36-byte LE header, u16 mm body, numpy) is branched before the picture path in ingest. Drops (wrong length, format, zero size, >1 MB) count as depth_dropped; unpaired (no phone line within ±60 ms) as depth_unpaired. Summary = median of non-zero depths over the middle third of rows for the L/C/R column thirds (null if none). Only the newest summary is kept.
- Phone lines ({"type":"phone"}): field-wise validation (an invalid field keeps the previous value), extras ignored, about 1 s of ts kept for pairing; never treated as motion.
- Vision events gain pos_x, pos_z, heading_deg, ar_tracking, depth_left/centre/right (null when older than 1 s) + depth_prompt (the exact depth text sent to Claude, or "Depth unavailable…").
- /device-test status shows pose, heading, tracking, LiDAR, depth L/C/R and the depth counters. The run API has no pose/depth.
- Check: tests/depth_check.py (with run_check_data.py setup/cleanup).

## Phase 8 implemented (2026-10-24): teach a route by walking
- backend/teach.py: teach_sessions ("tch-xxxx", key hash; plain key only while active, erased on finish/cancel/expiry), the same /api/ws/ingest socket (tch- prefix), a hidden draft route (teach_pending) whose checkpoints reuse the Phase 3 endpoints. Points: every 8th pixel → world via column-major ar_pose, 5 cm voxel dedupe, 200k cap, tracking "normal" only. Planes replaced per ar_planes set (malformed skipped). Trail every 0.25 m; turn detection >45° over 2 m windows, 2 m skip; Start/Turn N/End. 3 s JPEG ring, photo pick waits ~1 s, then nearest-first (up to 5 candidates) with the Sonnet person check; all people → "Needs photo". Save → RouteMemory (points.f32 + memory.json in storage) referenced by route_version.memory_id; builder saves copy memory_id. Idle expiry 2 h (background task). Client runs: practitioner-only trail on attempts (GET /api/attempts/{id}/trail).
- sensors.py: parse_depth/summarise_array; lines keep pose + tracking for pairing.
- Photos now carry route_id so route cascade deletes catch photos of removed checkpoints.
- Frontend: TeachStartForm (Routes), TeachWalk (/teach/:id), TeachReview (/teach/:id/review) with lazy Scene3D (r3f + drei, height colours, plane styles, trail, sprite markers, aria-label summary) + CheckpointCard list; lib/saveBlocker.js.
- In-memory map is lost on a backend restart (checkpoints survive in the DB).
- Check: tests/teach_walk_sim.py walk|save|cleanup.

## Backlog
- P1: Later-phase features (routes, checkpoints, exercises with key shown once at assignment, attempts, events, corrections), to be defined with the user.


## Phase 9 — Relevance policy (Oct 2026) DONE
- backend/cue_policy.py: pure deterministic decide(state, event, exercise, version, sensors, now) -> (cue, state); rules 1-5 (pause p0 / next checkpoint p2 / new entity p1 / on route / 3 s rate limit).
- backend/cue_runner.py: per-attempt in-memory policy state, 1 s timer (no frames 2 s, no usable 5 s), logs one 'cue' event per vision/vision_error (for_event_id) and spoken cues as 'guide' (reason=policy) pushed to GlassCam + phone polling.
- backend/test_hooks.py: check-only vision injection, mounted only when CUE_TEST_HOOK=1 (off by default).
- tests/cue_policy_check.py replay|e2e. No UI changes.
- Next (user plan): cue/policy UI; deferred checkpoint-2 match check after first real teach walk.

## Phase 10 — Start-grace fix + attempt review (Oct 2026) DONE
- Grace: the 2 s no-frames rule waits for the first frame after Start/Resume or 15 s; the 5 s no-usable rule counts from the first frame.
- Cue events store pos_x/pos_z, would_have_said and details; phone frames store heading/steps samples on the attempt (practitioner-only).
- GET /api/attempts/{id}/review (+ /review/points): header, timeline with plain-word reasons, 3D (aligned) or 2D (AR trail / dead reckoning) path.
- /review/{id} page: header, filters, Details JSON, 3D (Scene3D + projected dot buttons) or SVG 2D path, dot<->timeline linking; "Review" link on each attempt.
- Kept demo data: Client A, goal "Review demo (synthetic)": 3D attempt 48461db6-54af-4344-a634-30753164eb85, 2D attempt a59b1526-6c85-4c7b-992f-2854fd908502.

## Phase 11 — Policy fixes + corrections & route memory versions (Oct 2026) DONE
- Policy: "On route." no longer sets last_spoken / never rate-limits; skipped (nothing_to_say) <3 s after a real cue. Held-back checkpoint retried on the next result; held-back object retried only if seen again (same label+side, new distance, re-checked).
- known_entity: label + (positions within 2 m start-relative, else same checkpoint segment); reason "Known: chair confirmed in v2".
- attempts.route_version (latest version at creation; migrated from exercise pin); run/vision/policy/review use it; client page shows vN.
- Corrections (backend/corrections.py): Confirm/Edit/Dismiss per object item, one per item (409), next version copied from latest with change note; Remove from memory; GET /api/routes/{id}/history. Builder saves carry known entities + 3D memory.
- Review/route pages: version history, known-object markers (purple triangles) in 3D/2D, unpositioned listed.
- Data: 3D demo route has v2 "chair confirmed" (no position: demo run had no depth) + 1 correction.

## Phase 12 — Progress note + machine view (Oct 2026) DONE
- backend/notes.py: code-built text fact sheet (reuses review.py), Claude Sonnet 5.5 (NOTE_MODEL) draft with heading validation (1 retry), numbers check, 45 s timeout; progress_notes collection, one per attempt, read-only; client notes list + print view (/notes/{id}/print).
- backend/machine.py: one machine-view serializer (REPLAN_LEFT/RIGHT, authoritative false) used by review items, version history and GET /api/routes/{id}/memory?version=N (checkpoint positions start-relative for taught routes).
- Check note deleted after verification; demo data unchanged.


## Phase 13 — Demo recording + replay (2026-10-25)
- Recording: `record_demo` checkbox (Assign + New attempt), analysed frames only, person in vision result or Sonnet person check fail/person/timeout -> not stored (fail closed); EXIF-stripped JPEG + t_offset_ms/pose/depth/source in `recordings`; Recording badge; run page announces at Start; `recording.consider` asserts record_demo and not replay.
- Synthetic fallback: 12 AI-generated empty-corridor frames, 1.4 s apart, chair between Start and Turn 1, kept on "Review demo route 3D (synthetic)".
- Replay: practitioner (`/routes/:id/replay`) and public (`/demo`, Home "Try the demo"); same vision -> cue_policy pipeline, temperature 0 (`with_params`), original timing (drift <= 2 ms), ends after last frame, never records; Replay badge; 1920x1080 no-scroll screen.
- Public cap 3 running (429 "Demo busy, try again in a minute."), 24 h sweep (excludes practitioner replays, notes, corrections), orphan replays ended on restart.
- Backlog: real hardware recording on the demo route; sweep correction-exclusion only code-verified.

## Phase 14 — Polish (2026-10-25)
- Landing "/" (headline, subline, research line with CDC/ACVREP links, 3 steps, Try the demo / Open the practice workspace, /research link); old home at /workspace; logo /workspace in workspace, "/" on public pages; /replay/:id deep link.
- /research (CDC, ACVREP, Dove et al. verbatim quotes, "Still validating with practitioners" empty).
- Idempotent logged migration `phase14-demo-renames`: 3D demo route + checkpoints Entrance / Hallway turn / Reception desk across checkpoints, versions, events; 2D route "Lobby to elevator (synthetic)".
- Device test removed from nav/workspace (URL kept); unique page titles; inline confirm dialogs trap/restore focus + Escape; skip link on note print; placeholder contrast.
- axe-core: 0 serious/critical on 16 pages; regression scripts pass.

## Phase 15 — 3D demo replay + synthetic corridor model (2026-10-25)
- Replay screen uses shared Scene3D when the version has 3D memory: growing trail, now marker + heading arrow, cue dots (amber circle spoken / grey square held back), purple known-entity triangles, damped follow camera, Free look (orbit), reduced-motion fixed overview, sr-only summary; 2D fallback kept; fits 1920x1080.
- Migration `phase15-synthetic-model`: 38,540-point coloured corridor (floor, walls, left handrail, tactile strip, desk, chair at (0.6,-5.0)) on v1+v2; optional per-point RGB (`colors_path`); v2 chair position set; recording frame 2 centre depth 3.1 m.
- Review for replays: same 3D view with RGB + "Synthetic 3D model" label.
- Known gap: headless fps 13.5 (software WebGL); real-GPU fps unmeasured.

## Phase 16 — Landing redesign (2026-10-25)
- "/" only: navy hero (h1 ~70 px clamp, subline, Try the demo / Open the practice workspace) + lazy 3D corridor loop (15k points, scripted v1 spoken / v2 held-back passes from stored data, no attempts/AI), still-image fallback for reduced motion / no WebGL / failure.
- Stats band (7.1M CDC, 4,068 ACVREP, 1,700+ ratio, See the research), How it works with real app stills (WebP 15–30 KB, lazy), "What the specialist sees" live rows from att-iiri, closing band.
- New public read-only endpoints: GET /api/demo/scene, GET /api/demo/points (15k cap). Scene3D gained optional `view` (fixed camera aim).

## Phase 16b — Fixes (2026-10-25)
- Replay checkpoints: cause was vision never matching Hallway turn / Reception desk on the synthetic frames (near-identical landmark memories, no distinct turn/desk in frames). Replaced frames 7–8 (right turn + RECEPTION sign) and 11–12 (reception desk); replay shows reached checkpoints (filled markers, text, sr summary).
- Cropped frames 3, 5, 9 (date stamp / phone UI); old blobs unreferenced.
- Landing hero: 3D ~57% width, 454 px tall, caption card always over the view and alternating (also on still fallback); h1 57–68 px.

## Phase 17 (Oct 2026) - checkpoint detection
- One unusable frame = silent unusable_frame; pause only after 5 s with no usable result (unusable + vision_error together)
- Position as second signal (fresh pose within 1.0 m of the next checkpoint, route positions only); details.by picture/position
- Skip one: picture match on next+1 speaks it, logs silent checkpoint_skipped
- Review: Reached by picture/position, Missed checkpoint line, Blurry frame ignored as routine; header checkpoints_missed; fact sheet lists missed
- tests/cue_policy_check.py 45 cases; tests/myroom_reeval.py read-only re-evaluation

## Phase 18 (Oct 2026) - create a route from a 3D scan
- Routes > Create from 3D scan: name, required empty-space checkbox, .glb/.ply/.obj up to 100 MB, 8 MB chunked upload to local temp disk only (deleted after processing/failure/cancel; derived points .npz deleted on save/cancel; 6 h sweep)
- backend/scan.py (trimesh): 150k points, vertex/texture/height colours, unit + upright detection, floor detection, placement re-centring (Entrance=(0,0,0), facing -Z), save as route_memories kind=scan label "3D scan (uploaded by practitioner)"
- /scan/:id placement (click/drag/undo/move/remove + keyboard list), browser-rendered eye-height checkpoint pictures through the existing photo check, approve, save v1
- Shared alignment (cue_policy.alignment/to_route) for build_path, position rule and entity confirmation; scan routes rotate by the first 1.5 m walked
- Checks: tests/make_scan_meshes.py, tests/scan_check.py, tests/sim_scan_run.py

## Phase 19 (Oct 2026) - distinct-landmark warning
- backend/similarity.py: text Jaccard >= 0.6 or photo dHash Hamming <= 10 -> "Reads like checkpoint N..." on both cards (builder, teach review, scan pictures); never blocks Approve/Save
- POST /api/checkpoints/{id}/suggest-distinct: Sonnet with this photo + the other texts (distinct prompt), unapproves; failure -> "AI suggestion unavailable"
- migrations.phase19_demo_landmarks: demo frames 1/8/12 as photos + 3 distinct texts on checkpoints, v1, v2 (old photos unservable)
- Distance guard (REQ-605..608, approved): picture matches more than PICTURE_MAX_DIST_M=3.0 m from the matched checkpoint's position (fresh, aligned pose) are ignored and logged as a routine 'picture_too_far' silence; off without positions / stale pose / unaligned scan run. Demo chair story restored
