# Phase 3 Journeys
(Earlier journeys JRN-1..29 stay valid.)

- JRN-30: steps: open any page. expected: the top nav shows Clients, Routes and Device test; the current page is marked; keyboard Tab reaches all three.
- JRN-31: steps: open Clients, click "Client A (synthetic)". expected: the list shows both clients; the client page shows name and notes; there are no edit controls.
- JRN-32: steps: open the client page for an unknown id. expected: "Client not found".
- JRN-33: steps: open Routes. expected: "Test route (synthetic)" is listed with its checkpoint count and current version (0 / "Not saved yet"); a "New route" button is visible.
- JRN-34: steps: on a 390px-wide phone viewport, press New route, enter a name, add 3 checkpoints. expected: 3 numbered checkpoints, each with name, Take photo, Upload photo and landmark text; no horizontal scroll.
- JRN-35: steps: move checkpoint 3 up, then remove checkpoint 1. expected: the order updates and renumbers; Move up is disabled on the first, Move down on the last.
- JRN-36: steps: upload a large photo of an empty corridor. expected: the stored photo is about 1280px wide with its aspect ratio kept; landmark text shows a description of 25 words or fewer labelled "Suggested by AI".
- JRN-37: steps: upload a photo that shows a person. expected: "Retake: a person is in the photo"; no photo is stored or shown on the checkpoint; no description of the person.
- JRN-38: steps: add a photo while the AI call fails or times out. expected: "AI suggestion unavailable"; the photo is kept; the practitioner can type text and approve.
- JRN-39: steps: upload a text file, or a 20 MB file. expected: rejected with a clear message; nothing stored.
- JRN-40: steps: edit the suggested text. expected: the "Suggested by AI" label disappears.
- JRN-41: steps: approve 2 of 3 checkpoints. expected: "Save route" is disabled with a reason; Approve is disabled on any checkpoint missing a name, photo or text.
- JRN-42: steps: approve all, press Save route. expected: "Saved as version 1"; Routes shows the new route with 3 checkpoints, version 1; route_versions has v1 with a snapshot, author "J. Rivera (synthetic)" and created_at.
- JRN-43: steps: reopen the route, reorder two checkpoints. expected: they stay approved; Save is enabled.
- JRN-44: steps: change one checkpoint's text. expected: that checkpoint becomes unapproved; Save is disabled until it's re-approved.
- JRN-45: steps: re-approve and save. expected: "Saved as version 2"; the v1 snapshot is unchanged; current_version 2.
- JRN-46: steps: reload the builder mid-edit (unsaved). expected: draft checkpoints, photos and text are still there.
- JRN-47: steps: open Device test and run the wss check script. expected: Phase 2 behaviour is unchanged (Live, counters, cues).
