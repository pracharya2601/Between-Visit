# Phase 1 Requirements: Skeleton & Data Model
Version: phase-1

Goal: the FastAPI + MongoDB data model for all 10 collections, idempotent seed, health and list endpoints, and one accessible React home page. See ../overview.md.

## Collections (every one has `id` (uuid string) and `created_at` (ISO UTC))
- practices: name
- practitioners: practice_id, name, role
- clients: practice_id, display_name, notes, synthetic (true)
- routes: practice_id, name, current_version
- route_versions: route_id, version, checkpoints[], known_entities[], author, created_at
- checkpoints: route_id, order, name, photo_url, landmark_text, approved
- exercises: route_id, client_id, goal, cue_style (minimal|standard), silence_rules, stop_rule, stream_id, key
- attempts: exercise_id, status, started_at, ended_at
- attempt_events: attempt_id, t, type, text, spoken (bool), suppressed_reason, checkpoint, uncertain
- corrections: attempt_event_id, action (confirm|edit|dismiss), author, new_route_version

## Functional requirements
- REQ-1 [always] The system shall define a Pydantic model for each of the 10 collections with the fields listed above.
- REQ-2 [always] The system shall give every document an `id` and a `created_at`.
- REQ-3 [unwanted] If a client is built with synthetic not true, then the system shall reject it with a validation error.
- REQ-4 [unwanted] If an exercise has a cue_style other than "minimal" or "standard", then the system shall reject it with a validation error.
- REQ-5 [unwanted] If a correction has an action other than "confirm", "edit" or "dismiss", then the system shall reject it with a validation error.
- REQ-6 [always] The system shall create indexes on the foreign-key fields (practice_id, route_id, client_id, exercise_id, attempt_id, attempt_event_id). (interpreted)
- REQ-7 [event] When the backend starts while the practices collection is empty, the system shall insert the seed practice, practitioner and two clients from overview.md.
- REQ-8 [unwanted] If seed data already exists at startup, then the system shall insert no new documents.
- REQ-9 [event] When GET /api/health is called, the system shall return {"ok": true}. No failure mode.
- REQ-10 [event] When GET /api/practices is called, the system shall return a list of all practices.
- REQ-11 [event] When GET /api/practitioners is called, the system shall return a list of all practitioners.
- REQ-12 [event] When GET /api/clients is called, the system shall return a list of all clients.
- REQ-13 [always] The system shall leave Mongo `_id` out of every API response.
- REQ-14 [always] The system shall never return or display exercises.key. (interpreted)
- REQ-15 [always] The system shall serve the OpenAPI spec at /api/openapi.json.
- REQ-16 [event] When the home page loads, the system shall show the practice name, the practitioner name with role, and both client display names (no notes).
- REQ-17 [unwanted] If the backend is unreachable or returns no practice, then the home page shall show "Couldn't load practice data".
- REQ-18 [always] The system shall show the footer text from overview.md exactly on every page.
- REQ-19 [always] The system shall store no frames from client runs; only checkpoint photo_url of empty spaces exists in the model.

## Quality requirements
```
Q-1  Tag: Accessibility.Contrast
     Scale: text contrast ratio
     Meter: human / contrast checker
     Must: 4.5:1   Plan: 7:1
Q-2  Tag: Accessibility.Keyboard
     Scale: % of interactive/landmark elements reachable by Tab with a visible focus ring
     Meter: human
     Must: 100%   Plan: 100%
Q-3  Tag: Accessibility.TextSize
     Scale: base body font size in px
     Meter: human / devtools
     Must: 18   Plan: 20
Q-4  Tag: Data.Idempotency
     Scale: document count after 3 restarts vs after 1
     Meter: curl /api/clients count
     Must: equal   Plan: equal
Q-5  Tag: Privacy.Synthetic
     Scale: clients with synthetic != true
     Meter: mongo query
     Must: 0   Plan: 0
```
