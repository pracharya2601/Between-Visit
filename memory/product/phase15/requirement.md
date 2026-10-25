# Phase 15 Requirements: 3D Demo Replay + Synthetic Corridor Model
Version: phase-15

Goal: the demo replay becomes a 3D walk-through. The replay screen and replay reviews use the three.js view with a growing trail, a moving "now" marker, cue dots and known entities, on a richer synthetic 3D model of the demo corridor. See ../overview.md. Phases 1–14 must keep working. This is another user-approved one-off change to synthetic demo data (replacing the 3D memory on v1 and v2 and adding a position to the v2 chair).

## Replay screen (3D)
- REQ-490 [state] While the replay's route version has 3D memory, the replay screen shall show the shared three.js view (points, floor, walls, numbered checkpoint markers) instead of the 2D path panel.
- REQ-491 [always] On desktop the 3D view shall take about 60% of the width, with the frame image smaller beside it; at 1920×1080, 3D, frame, large caption, counts and labels shall all be visible with no scroll.
- REQ-492 [state] While the replay advances, the trail line shall grow up to the current position.
- REQ-493 [state] While the replay advances, a "now" marker with a short heading arrow shall move with the current pose.
- REQ-494 [event] When a cue event happens, a dot shall appear at its position: amber = spoken, grey = held back (routine silences excluded), with a shape difference + legend.
- REQ-495 [always] Known entities of the pinned version shall show as purple labelled triangles.
- REQ-496 [always] The default camera shall smoothly follow from behind and above the marker (damped, no jumps).
- REQ-497 [event] When "Free look" is toggled on, the system shall stop following and allow orbit and zoom; toggling off returns to follow.
- REQ-498 [state] While prefers-reduced-motion is set, the view shall use a fixed overview of the whole route with no camera motion (markers still update).
- REQ-499 [state] While the version has no 3D memory, the 2D panel shall remain as the fallback.
- REQ-500 [always] The view shall keep an updating text summary for screen readers (current checkpoint, cues so far, known entities); the canvas has an aria-label.
- REQ-501 [always] On small screens the layout shall stack (3D first, then frame, caption, counts).

## Synthetic 3D model for the demo route
- REQ-502 [event] When the migration runs, the system shall generate a synthetic 3D memory for "Entrance → hallway turn → reception desk (synthetic)" and attach it to BOTH v1 and v2, replacing the old simulated scan. Idempotent, logged; this route only.
- REQ-503 [always] The geometry shall be a corridor 1.8 m wide and 2.6 m high (no ceiling) from the Entrance (0,0,0) 10 m to the Hallway turn (0,0,−9.9), then turning right 6 m to the Reception desk (6,0,−10), in route-start coordinates (+Y up, −Z north, +X east).
- REQ-504 [always] The model shall include the floor, both walls, a handrail on the left wall, a yellow tactile strip down the middle of the floor, a reception desk at the end, and a chair against the right wall where the replay's chair cue happens.
- REQ-505 [always] The model shall have about 40,000 points with slight noise (~1–2 cm) and per-point colours like a real scan (grey/beige floor, off-white walls, metallic handrail, yellow strip, wood desk, dark chair).
- REQ-506 [always] The memory format shall support optional per-point RGB; the view shall use RGB when present, else height colouring as before. (interpreted)
- REQ-507 [always] The planes shall include the floor (grey) and the walls (see-through), as in the teach review.
- REQ-508 [always] The replay screen and reviews shall show the label "Synthetic 3D model" next to "Synthetic demo (AI-generated images)".
- REQ-509 [always] The replay trail (the synthetic recording's poses) shall be aligned to the model so the marker walks down the middle of the corridor and turns right at the Hallway turn. Adjust the recording's pose metadata if needed (synthetic data only).

## v2 chair position
- REQ-510 [event] When the migration runs, the system shall set the v2 known entity "chair" position (start-relative) to the model's chair location, matching where the replay's chair sighting is computed (within 1 m, interpreted).
- REQ-511 [always] After the change, replays on v2 shall still hold back the chair as "Known: chair confirmed in v2" (2 of 2), and replays on v1 shall still speak it (2 of 2).
- REQ-512 [always] The machine view and memory endpoint for v2 shall now show the chair's position.

## Review (3D)
- REQ-513 [always] /review for replay attempts shall use the same 3D view (full trail, cue dots, known entities, checkpoint markers; no animation) with the dot↔timeline linking as before.
- REQ-514 [always] Non-replay reviews shall keep working as before (3D when there's memory, else 2D).

## Quality requirements
```
Q-68 Tag: Demo.Visual
     Scale: elements cut off or a scroll needed at 1920×1080 on the replay screen
     Meter: screenshot mid-play
     Must: 0   Plan: 0
Q-69 Tag: Demo.Performance
     Scale: frame rate of the 3D view during replay on a typical laptop
     Meter: headless/requestAnimationFrame sampling
     Must: 30 fps   Plan: 60 fps
Q-70 Tag: Demo.Story
     Scale: v1 chair spoken / v2 chair held back across 2 replays each
     Meter: replays
     Must: 2/2 each   Plan: 2/2 each
Q-71 Tag: Model.Fidelity
     Scale: max distance (m) of the trail from the corridor centreline
     Meter: computed
     Must: 0.5   Plan: 0.2
```
