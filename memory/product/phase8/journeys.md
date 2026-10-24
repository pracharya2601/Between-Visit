# Phase 8 Journeys
(Earlier journeys stay valid. Check data is deleted afterwards. Real walks need a human; the builder uses a simulated walk.)

- JRN-101: steps: on Routes press "Teach by walking", enter a name. expected: the teach page shows a "tch-xxxx" stream ID and key with copy buttons, "Start at the route's entrance and face the way you'll walk.", and the live panel says "Not connected"; an empty name is refused.
- JRN-102: steps: connect GlassCam (simulated) over wss with the teach stream. expected: "Live"; a wrong key → 1008.
- JRN-103: steps: simulate an L-shaped corridor walk (10 m north, 90° turn, 6 m east) with phone lines (tracking normal), paired depth frames and 5 fps JPEGs. expected: metres walked ≈16; the points count grows; proposals Start, Turn 1, End (after Finish); no "vision" events.
- JRN-104: steps: during part of the walk, send tracking "limited". expected: those depth frames add no points.
- JRN-105: steps: send ar_planes with a floor, a wall and a door, then a new set without the door. expected: the kept set is replaced (no door).
- JRN-106: steps: make the frame nearest the turn contain a person, with a clean frame 0.5 s later. expected: Turn 1 uses the clean frame; no person photo is stored.
- JRN-107: steps: make all frames around a checkpoint contain people. expected: the checkpoint shows "Needs photo"; uploading a photo on the review page runs the person check + AI.
- JRN-108: steps: press Finish walk. expected: the review page shows a 3D view (orbit/zoom) with height-coloured points, a grey floor, see-through walls, a highlighted door, the trail line and markers 1–3; the browser gets ≤50,000 points; the list shows photo, name, AI text, Approve, Remove, Rename.
- JRN-109: steps: use the review page with keyboard/screen reader only. expected: the list gives every checkpoint's info and actions; the canvas has a text summary.
- JRN-110: steps: rename one, remove one, approve all, Save. expected: "Saved as version 1"; the route appears in Routes; route_version 1 has the 3D memory reference; the session is finished and the key no longer shown or retrievable.
- JRN-111: steps: assign the new route to Client A, open the run link, Start. expected: the run works as before; the run page/API never shows points, planes or trail.
- JRN-112: steps: during the run, send phone lines moving 3 m. expected: about 12 trail points stored on the attempt; no 3D points built; ar_planes ignored.
- JRN-113: steps: edit the route in the normal builder and save v2. expected: v2 still references the 3D memory.
- JRN-114: steps: Cancel a teach walk. expected: the session is cancelled, the key erased, the map discarded.
- JRN-115: steps: re-run wss_ingest_check.py, vision_check.py, depth_check.py. expected: earlier behaviour is unchanged.
- JRN-116: steps: after the checks, inspect the DB/storage. expected: check routes/sessions/attempts deleted; leftover blobs unservable and listed in the report.
