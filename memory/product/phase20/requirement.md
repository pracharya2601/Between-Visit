# Phase 20 Requirements: Live 3D While Walking
Version: phase-20 (starts after the Phase 19 distance guard is reported)

Goal: the practitioner watches a walk live in 3D on their Mac: the teach map building as they walk, and a "Watch live" view of a client's running attempt. Reuse Scene3D/Replay3D (same point look, follow camera, Free look, legend, reduced-motion overview). Frames are never stored. The client run page is unchanged. The 3 m rule and position checks are unchanged.

## A. Teach walk live map
- REQ-609 [state] While a teach session is active, /api/teach/{id}/points and /api/teach/{id}/scene shall be available (not only after Finish).
- REQ-610 [state] While active, TeachWalk/TeachLive shall show the 3D map building live: points re-fetched every 2 s (display downsample ≤50k, interpreted), scene every 1 s.
- REQ-611 [always] The live map shall show the walker's marker with a heading arrow at the newest ar_pose.
- REQ-612 [always] The live map shall show the trail growing.
- REQ-613 [always] The live map shall show proposed checkpoint markers appearing as they're proposed.
- REQ-614 [always] The teach page shall show a small live picture of the newest glasses frame via GET /api/teach/{id}/live-frame: the newest JPEG from the in-memory ring only, Cache-Control: no-store, 404/204 when none; never stored.
- REQ-615 [always] The counters and Finish/Cancel shall stay as they are.

## B. Watch live (client runs)
- REQ-616 [state] While an attempt is running or paused, the client page shall show a "Watch live" button opening /live/{attempt id}.
- REQ-617 [event] When GET /api/attempts/{id}/live is called, the system shall return the same "three" shape replay_state builds (scene, run_trail from the attempt's trail, floor_y, heading_deg from sensors_for, dots, entities) plus status, live (a frame in the last 3 s), last_checkpoint, cues_spoken, cues_held_back and the latest spoken caption.
- REQ-618 [unwanted] If the attempt is a replay or unknown, then /live shall return 404.
- REQ-619 [always] Taught and scan routes shall use their saved 3D model, with the run trail aligned by the shared alignment.
- REQ-620 [state] While the route has no 3D memory (photo routes, e.g. "My room") and the run sends DPT1 depth, the system shall build points live in memory from the run's depth (the same add_points logic as teach walks: every 8th pixel, 5 cm voxels, ar_tracking normal only), capped at 100k, served at GET /api/attempts/{id}/live/points (display downsample ≤50k).
- REQ-621 [event] When the run ends, the system shall drop those live points (never saved).
- REQ-622 [state] While there's no 3D memory and no depth, the live view shall show the trail on a floor grid.
- REQ-623 [always] The live page shall re-fetch /live every 1 s and points every 3 s.
- REQ-624 [always] The live page shall show the small live glasses picture via GET /api/attempts/{id}/live-frame (the newest frame only, no-store, never stored, only while running/paused, interpreted).
- REQ-625 [always] The live page shall show the latest caption in big text.
- REQ-626 [always] The live page shall show "Live" / "Not connected".
- REQ-627 [state] While the attempt has ended, the live page shall show "Run ended" with a link to the review, and the live frame endpoint shall return nothing.
- REQ-628 [always] The client run page and its API shall stay unchanged (no 3D, no frames, no pose).
- REQ-629 [always] The live view shall keep a text summary for screen readers (checkpoint, cues, status) and the reduced-motion overview.
- REQ-630 [always] "Client runs never build points" (Phase 8) is relaxed only for this in-memory live view on routes without 3D memory.

## Access
- REQ-631 [always] The live endpoints shall follow the decision recorded in "Access decision" below.

## Quality requirements
```
Q-85 Tag: Live.Latency
     Scale: seconds from a pose/caption change to the live page showing it
     Meter: simulated run
     Must: 3   Plan: 1.5
Q-86 Tag: Live.Privacy
     Scale: live frames persisted anywhere / served after the run ends
     Meter: inspection
     Must: 0   Plan: 0
Q-87 Tag: Live.Load
     Scale: bytes per points fetch
     Meter: network
     Must: ≤ 1 MB   Plan: ≤ 0.6 MB
```
