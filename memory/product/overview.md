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
| F-8 | Routes, checkpoints, exercises, attempts, events, corrections: features come later | practitioner | later |

## Phases
- Phase 1: Skeleton + data model + seed + read endpoints + home page → F-1..F-7. [requirement](phase1/requirement.md) · [journeys](phase1/journeys.md)
- Later phases: to be defined with the user.

## UI/UX Rules
- Large text (base ≥18px), high contrast (WCAG AA, aim for AAA), visible focus rings, keyboard reachable, semantic landmarks + ARIA labels.
- Footer text exactly: "Experimental practice tool used under the practitioner's direction. It doesn't replace the cane, the dog guide or the specialist, and it isn't a safety device."
- Error state copy: "Couldn't load practice data".

## Integrations
None in this phase. No auth.

## Edge Cases
- Synthetic people only: clients.synthetic must be true; the model rejects false.
- Never store frames from client runs. Only checkpoint photos of empty spaces (photo_url) are stored.
- exercises.key is a private access code for the client's run link. Never returned by list endpoints. In a later phase, the practitioner sees it exactly once, at the moment of assigning an exercise.
- Seeding is idempotent: restarting never creates duplicates.
- Backend down or empty data → the home page shows "Couldn't load practice data".

## Seed Data
- Practice: "Bay Mobility Practice"
- Practitioner: "J. Rivera (synthetic)", role "O&M specialist"
- Clients: "Client A (synthetic)", "Client B (synthetic)", synthetic: true
- No other collections are seeded.
