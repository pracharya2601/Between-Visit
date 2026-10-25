# Phase 12 Journeys
(Earlier journeys stay valid. Keep the Phase 10/11 demo data; delete check notes and any other check data afterwards.)

- JRN-163: steps: open the review of an ended attempt. expected: a "Draft progress note" button; on a running/not-started attempt it's disabled with "Available after the run ends".
- JRN-164: steps: press "Draft progress note" on the 3D demo attempt. expected: within ~15 s a text area with the six sections in order, labelled "Draft written by AI from the attempt log. Review before saving."; numbers match the header (checkpoints n of N, spoken/held back, help count).
- JRN-165: steps: inspect the request sent to the model (logs/test). expected: a text fact sheet only; no images, photos, depth, points or keys.
- JRN-166: steps: check the draft for invented details. expected: every event, number and name is in the log; missing info says "Not recorded"; the next-session focus is phrased as a suggestion.
- JRN-167: steps: simulate an AI failure. expected: "Couldn't draft a note. Try again."; nothing saved.
- JRN-168: steps: edit the text, press "Approve and save". expected: saved with author "J. Rivera (synthetic)" and time; the review shows it read-only with a collapsed "Original AI draft"; the button is gone.
- JRN-169: steps: try saving a second note or modifying the note via the API; try saving empty text. expected: 409 / no modify route; empty blocked.
- JRN-170: steps: open Client A's page. expected: the note is listed with date, route + version, author, Copy and Print; Copy announces "Copied"; Print shows the client, date, route, note, author and footer, no nav.
- JRN-171: steps: on the 3D demo review and route version history, open "Machine view" on the confirmed chair. expected: JSON with type "REPLAN_LEFT" (chair side right/ahead), authoritative false, source "BetweenVisit route memory", the route_id, version 2, the entity with segment {from 1, to 2}, position null (no depth in the demo), verified_by "J. Rivera (synthetic)", verified_at, and the matching advice.
- JRN-172: steps: (temporary route) confirm an object on the left with depth. expected: type "REPLAN_RIGHT", advice "…left of the path; keep right.", position with x, y (null), z, units "m", origin "route_start".
- JRN-173: steps: GET /api/routes/<3D demo>/memory, ?version=1, ?version=2. expected: latest = v2 with the chair; v1 has no entities; checkpoints have order, name, landmark_text and position (taught route); no photo links/points/planes/trail/keys.
- JRN-174: steps: GET the memory of the 2D demo route. expected: checkpoint positions null.
- JRN-175: steps: GET memory for an unknown route, version 99, and the hidden test route. expected: 404 each.
- JRN-176: steps: open the run page/API of a demo attempt. expected: no notes or machine view data.
