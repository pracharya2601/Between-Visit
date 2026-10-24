# Phase 8 Requirements: Teach a Route by Walking
Version: phase-8

Goal: the practitioner walks a route wearing GlassCam with the iPhone sensors. The server builds a light 3D memory (points, planes, trail) and proposes checkpoints with photos and AI landmark text. The practitioner reviews it in a 3D view plus an accessible list, and saves it as route v1. Assign and run are unchanged. See ../overview.md. Phases 1–7 must keep working. Check data is deleted afterwards (storage blobs can't be deleted, so make them unservable and report them).

## Teach session
- REQ-234 [always] The Routes page shall show a "Teach by walking" button.
- REQ-235 [event] When pressed, the system shall ask for a route name (required) and create a teach session with its own stream ID ("tch-" + 4 lowercase alphanumerics, unique across attempts and teach sessions) and a random key.
- REQ-236 [always] Teach sessions shall be stored in a new teach_sessions collection (id, created_at, route name, stream_id, key hash, status active|finished|cancelled|expired, updated_at). (interpreted)
- REQ-237 [state] While the session is active, the teach page shall show the stream ID and key with copy buttons (the key is retrievable for this page only).
- REQ-238 [event] When the walk is finished, cancelled or expired, the system shall erase the plain key.
- REQ-239 [always] The teach page shall show "Start at the route's entrance and face the way you'll walk."
- REQ-240 [always] The teach page shall show a live panel, refreshed every 1 s: "Live"/"Not connected", metres walked, 3D points so far, checkpoints proposed.
- REQ-241 [always] GlassCam shall connect to the existing /api/ws/ingest/{stream_id}?key= with the teach stream ID; wrong key → 1008; reconnects continue the same session; a new connection takes over.
- REQ-242 [event] When "Cancel walk" is pressed, the system shall end the session and discard its in-memory map and proposed checkpoints. (interpreted)
- REQ-243 [unwanted] If a session has no activity for 2 hours, then the system shall expire it. (interpreted)
- REQ-244 [state] While a stream is a teach session, the system shall run no per-frame vision.

## 3D points (teach sessions only)
- REQ-245 [state] While a teach session is active and ar_tracking is "normal", each paired depth frame shall add 3D points.
- REQ-246 [unwanted] If ar_tracking isn't "normal", then the system shall skip that depth frame for points.
- REQ-247 [always] For every 8th pixel (u and v step 8) with a non-zero reading d (metres): x_right = (u+0.5−cx)/fx×d; y_up = −(v+0.5−cy)/fy×d; camera point = (−y_up, x_right, −d); world = ar_pose (column-major 4×4) × [camera point, 1].
- REQ-248 [always] The system shall keep at most one point per 5 cm cube (voxel key = floor(world/0.05)).
- REQ-249 [unwanted] If 200,000 points are kept, then the system shall add no more points (and show "Point limit reached" in the live panel, interpreted).
- REQ-250 [always] Client runs shall never build points.

## Planes
- REQ-251 [event] When a phone line carries ar_planes (full current set, ≤32, at most 1/s), the system shall replace the session's kept plane set.
- REQ-252 [always] Each plane shall keep id, align (horizontal|vertical), class (floor|wall|ceiling|table|seat|door|window|none), transform (16 floats world-from-plane, column-major), center [x,y,z], extent [w,l], rotation_y and polygon [[x,z]…] (≤32, plane coords, y = 0). Unknown fields are ignored.
- REQ-253 [unwanted] If a plane is malformed, then the system shall skip that plane and keep the rest. (interpreted)
- REQ-254 [state] While the stream is a client attempt, ar_planes shall still be ignored.

## Trail
- REQ-255 [state] While a teach session is active, the system shall add a trail point (x, y, z, t) whenever the position has moved at least 0.25 m from the last trail point.
- REQ-256 [state] While a client attempt is running, the system shall store a trail point every 0.25 m on the attempt (x, z, t). Practitioner-only; never on the run page or its API.
- REQ-257 [always] Metres walked shall be the sum of trail segment lengths.

## Checkpoint proposals
- REQ-258 [event] When the first trail point is recorded, the system shall propose a "Start" checkpoint there.
- REQ-259 [event] When the walking direction (from the trail) turns more than 45° within about 2 m of walking, the system shall propose a checkpoint at the turn.
- REQ-260 [unwanted] If a proposal would be within 2 m of the previous proposal, then the system shall skip it. (interpreted)
- REQ-261 [event] When "Finish walk" is pressed, the system shall propose an "End" checkpoint at the last trail point.
- REQ-262 [always] Proposed checkpoints shall get default names "Start", "Turn 1", "Turn 2"… "End" (interpreted) and an order.
- REQ-263 [always] During teach, the server shall hold glasses frames from about the last 2–3 s in memory only (server receive time), to pick photos.
- REQ-264 [event] When a checkpoint is proposed, the system shall take the glasses frame nearest in time and run the existing person check + Claude Sonnet 5.5 landmark suggestion (≤25 words, "Suggested by AI").
- REQ-265 [unwanted] If that frame has a person, then the system shall try the other buffered frames within about 1 s either side, nearest first.
- REQ-266 [unwanted] If every candidate has a person or there's no frame, then the system shall flag the checkpoint "Needs photo" with no photo stored.
- REQ-267 [always] Accepted photos shall be resized to 1280px wide, EXIF-stripped and stored in object storage as before. All other frames shall be discarded. Frames are never stored otherwise.
- REQ-268 [unwanted] If the landmark AI fails, then the checkpoint shall show "AI suggestion unavailable" with editable text.

## Review page
- REQ-269 [event] When "Finish walk" is pressed, the system shall open a review page for that walk.
- REQ-270 [always] The review page shall show a three.js 3D view with orbit and zoom.
- REQ-271 [always] The 3D view shall show points coloured by height.
- REQ-272 [always] The 3D view shall show planes from their polygon placed by the transform (extent around center if the polygon is missing): floor grey, walls see-through, doors highlighted.
- REQ-273 [always] The 3D view shall show the trail line and numbered checkpoint markers matching the list.
- REQ-274 [always] The browser shall receive at most 50,000 points (downsampled for display only; the full set is saved).
- REQ-275 [always] Beside the 3D view (below on phones) shall be the checkpoint list: photo, name, AI text, Approve, Remove, Rename. This list is the accessible alternative; the canvas has an aria-label summary (points, planes, metres, checkpoints).
- REQ-276 [state] While a checkpoint is "Needs photo", the list shall offer Take/Upload photo using the existing pipeline (person check + AI).
- REQ-277 [always] Approve/re-approve rules follow Phase 3 (text/name/photo changes un-approve; Approve needs a name, photo and text).
- REQ-278 [state] While any checkpoint is unapproved or there are none, Save shall be disabled with a reason.
- REQ-279 [event] When Save is pressed, the system shall create the route and route_version 1 (snapshot, author J. Rivera (synthetic)) with the 3D memory (points, planes, trail) attached to that version in object storage.
- REQ-280 [event] When the route is saved, the system shall mark the session finished and erase the key.
- REQ-281 [always] Later versions saved in the normal builder shall keep referencing the same 3D memory. (interpreted)
- REQ-282 [always] The saved route shall appear in Routes and work with Assign exercise and the run page unchanged.
- REQ-283 [always] 3D memory and trails shall be practitioner-only; never on the run page or in its API, never in logs.

## Quality requirements
```
Q-36 Tag: Map.Correctness
     Scale: max error (m) between a known synthetic wall and its reconstructed points
     Meter: simulated walk with known geometry
     Must: 0.10   Plan: 0.05
Q-37 Tag: Map.Limits
     Scale: kept points; points sent to the browser
     Meter: simulated walk
     Must: ≤200,000 / ≤50,000   Plan: same
Q-38 Tag: Checkpoints.Proposal
     Scale: proposals for a simulated L-shaped walk (one 90° turn)
     Meter: simulated walk
     Must: exactly Start, Turn 1, End   Plan: same
Q-39 Tag: Perf.Review
     Scale: seconds to render the 3D view with 50k points on a mid phone
     Meter: human / headless timing
     Must: 5   Plan: 2 (estimate)
Q-40 Tag: Perf.Ingest
     Scale: ms server time per depth frame during teach
     Meter: timing
     Must: 50   Plan: 10 (estimate)
Q-41 Tag: Privacy.Frames
     Scale: frames stored other than accepted checkpoint photos
     Meter: inspection
     Must: 0   Plan: 0
```
