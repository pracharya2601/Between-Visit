# Phase 4 Requirements: Exercise Builder & Assignment
Version: phase-4

Goal: the practitioner assigns a saved route to a client as an exercise, gets a one-time run link with its stream ID and key, and can make new attempts from the client page. The client's run page is a placeholder. See ../overview.md. Phases 1–3 must keep working; /device-test with "att-test" is unchanged.

## Cleanup
- REQ-89 [event] When this phase deploys, the system shall delete the routes "Check route (synthetic)" and "Library entrance (synthetic)" with their checkpoints and route_versions.
- REQ-90 [event] When those routes are deleted, the system shall delete their photos from object storage.
- REQ-91 [unwanted] If object storage can't delete a file, then the system shall make that photo unservable (proxy returns 404) and the builder shall report it. (interpreted)
- REQ-92 [always] The Routes list shall not show "Test route (synthetic)" (e.g. an is_test flag). It stays in the DB for /device-test.
- REQ-93 [unwanted] If the test route is opened by URL or targeted for assignment, then the system shall refuse it (404 or "not available"). (interpreted)

## Data model
- REQ-94 [always] Exercises shall store route_id, route_version (pinned, interpreted), client_id, goal, cue_style, silence_rules {stay_silent_on_route: bool, no_repeat: bool, note: str|null}, stop_rule.
- REQ-95 [always] Attempts shall store exercise_id, stream_id (unique), key hash, status, started_at, ended_at.
- REQ-96 [always] A new attempt shall have status "not_started" with null started_at and ended_at. (interpreted)

## Assign exercise
- REQ-97 [state] While a route has current_version ≥ 1, its builder/detail shall show an "Assign exercise" button.
- REQ-98 [state] While a route has never been saved, "Assign exercise" shall not be shown.
- REQ-99 [always] The form shall have a Client select listing all clients.
- REQ-100 [always] The form shall have a Goal text field, placeholder "Walk from the entrance to the reception desk using the three landmarks".
- REQ-101 [always] The form shall offer Cue style "Minimal (checkpoint names only)" or "Standard (checkpoint plus landmark)", with Standard selected by default.
- REQ-102 [always] The form shall have "Stay silent while on route" checked by default.
- REQ-103 [always] The form shall have "Don't repeat a cue for the same thing" checked by default.
- REQ-104 [always] The form shall have an optional silence note field.
- REQ-105 [always] The form shall have a Stop-and-contact rule field prefilled with "If you feel unsure, stop, press Help and wait for my call."
- REQ-106 [unwanted] If no client is selected, or the goal or stop rule is empty, then the system shall block submit with a field-level message.
- REQ-107 [event] When the form is submitted, the system shall create the exercise pinned to the route's current_version.
- REQ-108 [event] When the exercise is created, the system shall create its first attempt with a new stream ID "att-" + 4 lowercase letters/digits (unique, retrying on collision) and a new random key stored as a hash.
- REQ-109 [unwanted] If the creation fails, then the system shall show an error and create no partial exercise without an attempt. (interpreted)
- REQ-110 [event] When assignment succeeds, the system shall show a confirmation with the run link "<public origin>/run/{attempt id}#key=<key>", the stream ID and the key, each with a copy button.
- REQ-111 [always] The confirmation shall show the note "The client also sees these on their run page."
- REQ-112 [always] The confirmation shall tell the practitioner the key is shown only once.
- REQ-113 [event] When the confirmation is closed, the system shall never show that key again anywhere.
- REQ-114 [always] No API response other than the create response shall contain a plain key or key hash.
- REQ-115 [event] When the route is edited and saved as a new version later, the system shall leave existing exercises pinned to their original version.

## Client page
- REQ-116 [always] The client page shall list each exercise for that client with goal, route name, pinned version ("v2") and cue style.
- REQ-117 [always] Under each exercise it shall list the attempts with status, stream ID and run link /run/{attempt id} (no key).
- REQ-118 [state] While a client has no exercises, the page shall show "No exercises assigned yet".
- REQ-119 [event] When "New attempt" is pressed on an exercise, the system shall create another attempt with a new stream ID and a new key.
- REQ-120 [event] When the new attempt is created, the system shall show the same one-time confirmation (link with #key, stream ID, key, copy buttons).
- REQ-121 [always] Older attempts shall stay listed and valid after a new attempt is created. (interpreted)

## /run/{attempt id} placeholder
- REQ-122 [event] When the run page opens, the system shall show the exercise goal and the stream ID.
- REQ-123 [state] While the link contains #key=…, the page shall show the key (read from the fragment, never sent in a URL or query).
- REQ-124 [unwanted] If the link has no key, then the page shall show "This link is missing its key. Ask your practitioner for a new attempt."
- REQ-125 [unwanted] If the key in the link doesn't match the attempt (checked via a POST body or header, never the URL), then the page shall show "This link's key isn't valid." (interpreted)
- REQ-126 [unwanted] If the attempt id is unknown, then the page shall show "Run not found".
- REQ-127 [always] The run page shall use the accessibility rules (large text, high contrast, screen-reader labels) and show the footer; no practitioner nav. (interpreted)
- REQ-128 [always] A new attempt's stream ID and key shall work with /api/ws/ingest (connects, first message {"viewers":0}).

## Quality requirements
```
Q-17 Tag: Privacy.KeyExposure
     Scale: places a key appears after the confirmation is closed (API responses, logs, client page)
     Meter: grep logs + inspect GET responses
     Must: 0   Plan: 0
Q-18 Tag: Data.Integrity
     Scale: exercises without an attempt, or with a wrong pinned version
     Meter: DB query after 3 assignments + 1 route re-save
     Must: 0   Plan: 0
Q-19 Tag: Usability.Assign
     Scale: minutes for a first-time practitioner to assign an exercise and copy the link
     Meter: human
     Must: 3   Plan: 1 (estimate)
Q-20 Tag: Mobile.Usability
     Scale: horizontal scroll or clipped controls at 390px on the form, confirmation, client page and run page
     Meter: screenshot
     Must: 0   Plan: 0
```
