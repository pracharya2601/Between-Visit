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

## Backlog
- P1: Later-phase features (routes, checkpoints, exercises with key shown once at assignment, attempts, events, corrections), to be defined with the user.
