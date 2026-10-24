# Phase 1 Journeys

- JRN-1 — steps: call GET /api/health. expected: 200 with body {"ok": true}.
- JRN-2 — steps: call GET /api/practices. expected: one item named "Bay Mobility Practice" with id and created_at, no `_id`.
- JRN-3 — steps: call GET /api/practitioners. expected: one item "J. Rivera (synthetic)", role "O&M specialist", practice_id matching the practice.
- JRN-4 — steps: call GET /api/clients. expected: exactly "Client A (synthetic)" and "Client B (synthetic)", both synthetic: true, same practice_id.
- JRN-5 — steps: restart the backend twice, call GET /api/clients. expected: still exactly 2 clients, 1 practice, 1 practitioner.
- JRN-6 — steps: open the home page. expected: shows "Bay Mobility Practice", "J. Rivera (synthetic)" with "O&M specialist", "Client A (synthetic)" and "Client B (synthetic)"; client notes not shown.
- JRN-7 — steps: look at the bottom of the home page. expected: footer reads exactly "Experimental practice tool used under the practitioner's direction. It doesn't replace the cane, the dog guide or the specialist, and it isn't a safety device."
- JRN-8 — steps: stop the backend, reload the home page. expected: "Couldn't load practice data" shown; footer still visible.
- JRN-9 — steps: Tab through the home page. expected: visible focus ring on every focusable element; header/main/footer landmarks with ARIA labels; large high-contrast text.
- JRN-10 — steps: try to build a client model with synthetic false, an exercise with cue_style "fast", a correction with action "delete". expected: each raises a validation error.
- JRN-11 — steps: inspect Mongo after startup. expected: all 10 collections are defined in code; routes/route_versions/checkpoints/exercises/attempts/attempt_events/corrections hold no seed data; no API returns an exercise `key`.
- JRN-12 — steps: open /api/openapi.json. expected: spec lists /api/health, /api/practices, /api/practitioners, /api/clients.
