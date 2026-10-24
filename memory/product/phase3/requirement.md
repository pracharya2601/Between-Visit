# Phase 3 Requirements: Practitioner Workspace & Route Builder
Version: phase-3

Goal: the practitioner can browse clients and routes, then build or edit a route on a phone browser. They add ordered checkpoints with a photo of an empty space and an AI-suggested landmark, approve each one, and save the route as a new version. See ../overview.md. Phase 1 and 2 journeys must keep working (test route, /device-test, ingest).

## Navigation & lists
- REQ-54 [always] Every page shall show top navigation with links "Clients", "Routes", "Device test", the current page marked with aria-current="page".
- REQ-55 [always] The Clients page shall list every client by display name, each linking to its client page.
- REQ-56 [event] When a client page opens, the system shall show the client's display name and notes (read-only).
- REQ-57 [unwanted] If the client id is unknown, then the system shall show "Client not found".
- REQ-58 [always] The Routes page shall list every route with its name, number of checkpoints and current version.
- REQ-59 [always] The Routes page shall show a "New route" button that opens an empty route builder.
- REQ-60 [always] A route that has never been saved shall show current version 0 (e.g. "Not saved yet"). (interpreted)
- REQ-61 [event] When a route in the list is opened, the system shall load it into the route builder for editing.

## Route builder (must work on a phone browser, 360–430px wide)
- REQ-62 [always] The builder shall have a route name field.
- REQ-63 [event] When "Add checkpoint" is pressed, the system shall append a new checkpoint at the end of the list.
- REQ-64 [event] When "Remove" is pressed on a checkpoint, the system shall delete it and renumber the rest.
- REQ-65 [event] When "Move up" or "Move down" is pressed, the system shall swap the checkpoint with its neighbour and renumber the order.
- REQ-66 [state] While a checkpoint is first, its "Move up" shall be disabled; while it's last, "Move down" shall be disabled.
- REQ-67 [always] Each checkpoint shall have a name field, one photo and a landmark text field.
- REQ-68 [always] Each checkpoint shall offer "Take photo" (camera capture on phone) and "Upload photo" (file picker).
- REQ-69 [event] When a photo is added, the system shall resize it to about 1280px wide (no upscaling), remove EXIF/GPS metadata, and send it to Claude Sonnet 5.5 vision via the Emergent LLM key.
- REQ-70 [always] The prompt shall ask for one stable landmark description useful for orientation by a blind or low-vision person, at most 25 words; if a person is visible, return exactly "Retake: a person is in the photo" and describe no one.
- REQ-71 [event] When Claude returns a description, the system shall store the photo in Emergent Object Storage as route memory, set photo_url, and put the text into landmark text labelled "Suggested by AI".
- REQ-72 [unwanted] If the description is over 25 words, then the system shall trim it to 25 words. (interpreted)
- REQ-73 [unwanted] If Claude returns "Retake: a person is in the photo", then the system shall discard the photo without storing it and show "Retake: a person is in the photo".
- REQ-74 [unwanted] If Claude fails or times out (about 30s), then the system shall show "AI suggestion unavailable", keep the photo, and leave the landmark text editable.
- REQ-75 [unwanted] If the file isn't an image, or is over 15 MB, then the system shall reject it with a clear message and store nothing. (interpreted)
- REQ-76 [event] When the practitioner edits the landmark text, the system shall remove the "Suggested by AI" label.
- REQ-77 [event] When "Approve" is pressed on a checkpoint, the system shall set approved true and show it as approved.
- REQ-78 [unwanted] If a checkpoint lacks a name, a photo or landmark text, then its "Approve" shall be disabled. (interpreted)
- REQ-79 [event] When an approved checkpoint's text, name or photo changes, the system shall set approved false.
- REQ-80 [always] Reordering checkpoints shall not change their approved state.
- REQ-81 [state] While any checkpoint is unapproved, or there are no checkpoints, or the route name is empty, "Save route" shall be disabled with a visible reason.
- REQ-82 [event] When "Save route" is pressed, the system shall create a route_version with version = current_version + 1, a snapshot of the ordered checkpoints, author "J. Rivera (synthetic)" and created_at.
- REQ-83 [event] When a version is saved, the system shall set routes.current_version to that version and show "Saved as version N".
- REQ-84 [always] Saved route_versions shall never be modified.
- REQ-85 [unwanted] If saving fails, then the system shall show an error and keep the builder's contents.
- REQ-86 [always] Draft checkpoints shall persist in the checkpoints collection, so reloading the builder keeps the work. (interpreted)
- REQ-87 [always] Photos shall be served to the browser through a backend endpoint; no raw storage keys or secrets are exposed. (interpreted)
- REQ-88 [always] All new pages shall meet the Phase 1 accessibility rules (labelled controls, keyboard operable, aria-live for AI/approve/save status, 44px touch targets) and show the footer.

## Quality requirements
```
Q-11 Tag: AI.Quality
     Scale: % of 5 empty-space photos that get a usable landmark description of 25 words or fewer
     Meter: human
     Must: 80%   Plan: 100%
Q-12 Tag: AI.PersonSafety
     Scale: photos with a visible person that are stored or described
     Meter: 3 trial photos with a person
     Must: 0   Plan: 0
Q-13 Tag: AI.Latency
     Scale: seconds from photo picked to suggestion shown
     Meter: 5 trials
     Must: 20   Plan: 8 (estimate)
Q-14 Tag: Mobile.Usability
     Scale: horizontal scroll or clipped controls at 390px width
     Meter: screenshot at 390x844
     Must: 0   Plan: 0
Q-15 Tag: Photo.Fidelity
     Scale: stored photo width px; aspect ratio preserved
     Meter: inspect a stored photo
     Must: ≤1280 and not stretched   Plan: 1280 for large inputs
Q-16 Tag: Data.Versioning
     Scale: earlier version snapshots changed after a later save
     Meter: compare v1 before and after saving v2
     Must: 0   Plan: 0
```
