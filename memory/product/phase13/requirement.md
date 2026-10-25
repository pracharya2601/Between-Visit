# Phase 13 Requirements: Demo Recording & Replay
Version: phase-13

Goal: the team records an empty-space run once (frames analysed ~1/s + pose + depth, never with people), and anyone (judges without hardware) can replay it through the same live pipeline on v1 or the latest route version and see cues spoken or held back as it plays. This is a deliberate, narrow exception to "never store frames" (see overview Edge Cases). Phases 1–12 must keep working; the existing demo data is kept.

## Recording
- REQ-420 [always] The Assign exercise form and the "New attempt" action shall offer a checkbox "Record this run as a demo (empty space, team only)", unchecked by default.
- REQ-421 [always] Attempts shall store record_demo (bool).
- REQ-422 [state] While a recorded attempt is running, the system shall consider storing each frame that was actually analysed by vision (~1/s), never skipped frames.
- REQ-423 [unwanted] If the vision result contains a person entity, then the system shall not store that frame.
- REQ-424 [event] When the vision result has no person, the system shall run the Sonnet person check (the same as for checkpoint photos) before storing.
- REQ-425 [unwanted] If the Sonnet check finds a person, fails or times out, then the system shall not store the frame (fail closed).
- REQ-426 [event] When both checks pass, the system shall store the frame (JPEG, as received, EXIF-stripped) in object storage with t_offset_ms (from Start, paused time excluded), pose {x, z, heading_deg, ar_tracking}, depth {left, centre, right}, and source.
- REQ-427 [always] Recordings shall be stored in a recordings collection {id, route_id, route_version, attempt_id|null, kind real|synthetic, label, frames[], created_at}. (interpreted)
- REQ-428 [always] Normal (unticked) runs shall never store frames.
- REQ-429 [state] While an attempt is recorded, the client page shall show a "Recording" badge on it.
- REQ-430 [event] When Start is pressed on a recorded attempt, the run page shall announce "This run is recorded as a demo."
- REQ-431 [event] When a recorded attempt ends with at least 1 stored frame, its recording shall become available on the route. (interpreted)

## Synthetic fallback
- REQ-432 [always] The builder shall create one synthetic recording for "Review demo route 3D (synthetic)": about 12 AI-generated empty-corridor frames (no people), at ≤1.5 s spacing, following the route's checkpoints in order, with a chair visible between checkpoints 1 and 2, and synthetic pose + depth.
- REQ-433 [always] The synthetic recording shall pass the same two person checks before storage.
- REQ-434 [always] The synthetic recording shall be labelled on screen "Synthetic demo (AI-generated images)".
- REQ-435 [state] While a real recording exists for the route, the replay shall default to the newest real recording and offer the synthetic one as a second option.

## Replay
- REQ-436 [state] While a route has a recording, the route page shall show "Replay demo run".
- REQ-437 [always] Replay shall offer a choice "On v1 (before corrections)" or "On latest version", plus the recording choice when more than one exists.
- REQ-438 [event] When a replay starts, the system shall create a new attempt (flag replay=true, recording_id, public true/false) on the recording's exercise, pinned to the chosen version, status running.
- REQ-439 [event] When a replay runs, the system shall feed each recorded frame at its original timing, with its pose and depth set as the sensor state, through the same pipeline: vision → policy → events → cues.
- REQ-440 [always] Replay vision calls shall use temperature 0.
- REQ-441 [event] When the last frame has been processed, the system shall end the attempt (ended_at set).
- REQ-442 [always] Replay attempts shall never record frames.
- REQ-443 [always] Replay attempts shall be marked "Replay" on the client page and their review works as normal.

## Replay screen
- REQ-444 [always] The replay screen shall show the current frame.
- REQ-445 [always] The replay screen shall show a large caption (≥48px at 1920 wide, aria-live="assertive") with the newest spoken cue.
- REQ-446 [always] The replay screen shall speak spoken cues with the browser voice, with a mute toggle (default on, i.e. not muted), started by a "Start replay" button (user gesture).
- REQ-447 [always] The replay screen shall show the last checkpoint reached.
- REQ-448 [always] The replay screen shall show a live count "Cues spoken: X · held back: Y" (routine silences excluded).
- REQ-449 [always] The replay screen shall show a 2D top-down path drawing as it plays, with checkpoints and known entities of the pinned version. (interpreted: 2D, not 3D)
- REQ-450 [always] The replay screen shall show the version ("Replaying on v1 (before corrections)" / "on v2 (latest)") and, for synthetic, "Synthetic demo (AI-generated images)".
- REQ-451 [always] At 1920×1080 the frame, caption, counts and path shall all be visible at once with no scrolling.
- REQ-452 [event] When the replay ends, the screen shall show a link to the attempt's review.
- REQ-453 [always] The replay screen shall show the footer disclaimer and stay usable on smaller screens (stacked).

## Try the demo (public)
- REQ-454 [always] The home page shall show "Try the demo", opening the replay screen for "Review demo route 3D (synthetic)" with the version choice. No login.
- REQ-455 [unwanted] If 3 public replays are already running, then the system shall refuse with "Demo busy, try again in a minute." (practitioner-side replays don't count, interpreted).
- REQ-456 [always] Public replay attempts shall be auto-deleted (with their events) 24 h after creation.
- REQ-457 [always] Auto-delete shall never touch practitioner-started replays, nor any attempt with corrections or a saved note.
- REQ-458 [always] The public replay screen shall expose only replay data: frames, cues, path and counts of that replay; no keys, no other attempts' data.
- REQ-459 [unwanted] If the route has no recording, then the screen shall show "No demo recording yet."

## Quality requirements
```
Q-59 Tag: Privacy.Recording
     Scale: stored frames containing a person
     Meter: recording check with person frames mixed in
     Must: 0   Plan: 0
Q-60 Tag: Privacy.NormalRuns
     Scale: frames stored from unticked runs
     Meter: inspection after a normal run
     Must: 0   Plan: 0
Q-61 Tag: Demo.Story
     Scale: on synthetic replays, chair spoken on v1 AND held back as known on v2
     Meter: 2 replays each
     Must: ≥1 of 2 each   Plan: 2 of 2 each
Q-62 Tag: Demo.Layout
     Scale: scroll needed or element cut off at 1920×1080
     Meter: screenshot
     Must: 0   Plan: 0
Q-63 Tag: Demo.Concurrency
     Scale: public replays running simultaneously
     Meter: 4 concurrent starts
     Must: ≤3 (4th busy)   Plan: same
Q-64 Tag: Demo.Timing
     Scale: drift (s) between the recorded and replayed frame times over the replay
     Meter: timestamps
     Must: 1.0   Plan: 0.3
```
