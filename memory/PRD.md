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

## Backlog
- P1: Later-phase features (routes, checkpoints, exercises with key shown once at assignment, attempts, events, corrections), to be defined with the user.
