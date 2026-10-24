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

## Backlog
- P1: Later-phase features (routes, checkpoints, exercises with key shown once at assignment, attempts, events, corrections), to be defined with the user.
