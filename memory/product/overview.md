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
| F-8 | Exercises, events, corrections UI: later | practitioner | later |

## Phases
- Phase 1: Skeleton + data model + seed + read endpoints + home page → F-1..F-7. [requirement](phase1/requirement.md) · [journeys](phase1/journeys.md)
- Phase 2: Device ingest, no vision → F-9..F-12. [requirement](phase2/requirement.md) · [journeys](phase2/journeys.md)
- Phase 3: Practitioner workspace + route builder → F-13..F-18. [requirement](phase3/requirement.md) · [journeys](phase3/journeys.md)
- Later phases: to be defined with the user.

## UI/UX Rules
- Large text (base ≥18px), high contrast (WCAG AA, aim for AAA), visible focus rings, keyboard reachable, semantic landmarks + ARIA labels.
- Footer text exactly: "Experimental practice tool used under the practitioner's direction. It doesn't replace the cane, the dog guide or the specialist, and it isn't a safety device."
- Error state copy: "Couldn't load practice data".

## Integrations
None in Phase 1. No auth.
- Phase 2: none external.
- Phase 3: Claude Sonnet 5.5 (vision) via the Emergent LLM key (emergentintegrations), for landmark suggestions. Emergent Object Storage for checkpoint photos.

## Edge Cases
- Synthetic people only: clients.synthetic must be true; the model rejects false.
- Never store frames from client runs. Only checkpoint photos of empty spaces (photo_url) are stored.
- (Phase 2) stream_id + key live on attempts, not exercises. The key is a private access code; it's never returned by list endpoints or written to logs. It's stored hashed. Only the seeded test attempt's key is shown, on /device-test. Later, the practitioner sees a new attempt's key exactly once, when it's created.
- Frames are never stored: count, last time, last size, then discard.
- Seeding is idempotent: restarting never creates duplicates.
- Backend down or empty data → the home page shows "Couldn't load practice data".

## Seed Data
- Practice: "Bay Mobility Practice"
- Practitioner: "J. Rivera (synthetic)", role "O&M specialist"
- Clients: "Client A (synthetic)", "Client B (synthetic)", synthetic: true
- No other collections are seeded.
