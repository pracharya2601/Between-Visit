# Phase 18 Requirements: Create a Route from a 3D Scan
Version: phase-18

Goal: a third way to create a route, next to "Teach by walking" and the photo builder. The practitioner uploads a phone 3D scan (Polycam / Scaniverse / 3D Scanner App), places the Entrance + facing and the checkpoints on it, gets rendered checkpoint pictures with AI landmark text, approves them, and saves v1. Everything downstream (Scene3D, Replay3D, review, replay, policy) works unchanged. Phases 1–17 must keep working.

## Upload
- REQ-566 [always] The Routes page shall offer "Create from 3D scan": route name (required), then a file upload accepting .glb (primary), .ply and .obj, max 100 MB.
- REQ-567 [always] A required checkbox "I scanned an empty space (no people)" shall gate the upload.
- REQ-568 [always] Uploads shall work through the public preview URL up to 100 MB; if a single request is blocked by size limits, use chunked upload. (interpreted)
- REQ-569 [always] The uploaded file shall live only on the server's local temp disk (never object storage) and shall be deleted once the points are saved, or on any failure/cancel.
- REQ-570 [unwanted] If the file has no geometry, can't be parsed, is the wrong type or is over 100 MB, then the system shall reject it with a clear message (e.g. "This file has no 3D geometry we can use.") and store nothing.

## Points
- REQ-571 [event] When a file is accepted, the system shall load the mesh (trimesh) and sample about 150,000 surface points with colours (vertex colour, else texture colour, else height colours).
- REQ-572 [event] When the mesh is loaded, the system shall detect units automatically and show the measured size ("about 4.2 × 3.1 m") with a unit selector (m / cm / mm) that rescales.
- REQ-573 [event] When the mesh is loaded, the system shall stand it upright automatically (Y-up), with a "Turn upright" button cycling the up-axis if it still looks wrong.
- REQ-574 [always] The system shall detect the floor (the lowest wide horizontal layer) so placement clicks land on the floor plane. (interpreted)
- REQ-575 [always] Points shall be saved as a normal route_memories record (points.f32, colours, memory.json) with label "3D scan (uploaded by practitioner)", exactly like save_teach, so Scene3D, Replay3D, review and replay work unchanged.

## Place the route
- REQ-576 [always] The placement screen shall reuse Scene3D with orbit.
- REQ-577 [event] When the practitioner clicks the floor, the system shall place the Entrance there.
- REQ-578 [event] When the practitioner drags from the Entrance, the system shall set the facing direction (an arrow shown).
- REQ-579 [event] When the practitioner clicks again, the system shall add checkpoints in order; the line Entrance → checkpoints is the route trail (memory.json trail).
- REQ-580 [always] The screen shall offer Undo, Move (drag a checkpoint on the floor) and Remove for checkpoints.
- REQ-581 [always] Placement shall be keyboard-operable as far as practical, with an accessible list of placed checkpoints (name, order, distance from the previous one) as the alternative to the 3D view. (interpreted)
- REQ-582 [event] When placement is confirmed, the system shall rotate and shift the saved model (points, trail, checkpoint positions) so Entrance = (0,0,0) on the floor and the facing direction = −Z, matching run alignment.
- REQ-583 [always] Checkpoint positions shall be saved (start-relative) so the position signal (Phase 17) and the memory endpoint work.

## Checkpoint pictures
- REQ-584 [event] When placement is confirmed, the browser shall render the 3D view from each checkpoint's spot at 1.6 m eye height, facing the next checkpoint (the last faces the approach direction), and send each image through the existing checkpoint photo upload (person check + Sonnet landmark text, resize, EXIF strip).
- REQ-585 [always] Each checkpoint shall allow replacing the render with Take/Upload photo (the same checks).
- REQ-586 [always] Approve per checkpoint as in Phase 3; Save is enabled only when all are approved → route v1 (author J. Rivera (synthetic)), with the scan memory attached.
- REQ-587 [always] The first checkpoint shall be the Entrance (named "Entrance" by default, editable). (interpreted)

## Runs on scan routes
- REQ-588 [always] One shared alignment function shall be used by build_path (review/replay), cue_policy (position signal) and entity confirmation: translate the run start to (0,0,0), then rotate the run so the direction of its first 1.5 m of walking matches the Entrance facing (−Z).
- REQ-589 [state] While the client hasn't walked 1.5 m yet, the position signal shall be off for scan routes. (interpreted)
- REQ-590 [always] Other route types shall keep their current alignment.

## Quality requirements
```
Q-78 Tag: Scan.Ingest
     Scale: seconds to process a 50 MB .glb to points
     Meter: timing
     Must: 60   Plan: 20 (estimate)
Q-79 Tag: Scan.Privacy
     Scale: uploaded files remaining on disk/storage after save or failure
     Meter: inspection
     Must: 0   Plan: 0
Q-80 Tag: Scan.Alignment
     Scale: angle error (°) between a simulated run's first 1.5 m and the Entrance facing after alignment
     Meter: computed
     Must: 5   Plan: 1
Q-81 Tag: Scan.Pictures
     Scale: rendered checkpoint pictures that give a usable landmark text
     Meter: human, 4 checkpoints on a test scan
     Must: 50%   Plan: 100%
```
