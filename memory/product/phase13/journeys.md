# Phase 13 Journeys
(Earlier journeys stay valid. Keep the existing demo data + the synthetic recording; delete other check data. Recorded check frames can't be deleted from storage, so keep any real-recording check tiny and make its frames unservable after.)

- JRN-177: steps: open Assign exercise and New attempt. expected: the checkbox "Record this run as a demo (empty space, team only)", unchecked.
- JRN-178: steps: create a recorded attempt, Start on the run page. expected: announces "This run is recorded as a demo."; the client page shows a "Recording" badge.
- JRN-179: steps: stream frames on the recorded attempt (some with a person). expected: only analysed frames with no person (both checks) are stored with t_offset, pose and depth; person frames are not stored.
- JRN-180: steps: do a normal (unticked) run. expected: no frames stored.
- JRN-181: steps: open the 3D demo route page. expected: "Replay demo run" with "On v1 (before corrections)" / "On latest version"; the synthetic recording is labelled "Synthetic demo (AI-generated images)".
- JRN-182: steps: replay on v1. expected: a new replay attempt pinned to v1; frames play at the original timing; the screen shows the frame, a large caption, voice (mute works), the checkpoint reached, "Cues spoken · held back" counts, the path drawing; the chair is spoken between checkpoints 1 and 2; at the end, a link to the review.
- JRN-183: steps: replay on the latest version (v2). expected: the chair is held back as "Known: chair confirmed in v2"; counts differ accordingly.
- JRN-184: steps: screenshot the replay screen at 1920×1080. expected: frame, caption, counts and path all visible with no scrolling; the caption is large.
- JRN-185: steps: on the home page click "Try the demo". expected: the replay screen for the 3D demo route, no login.
- JRN-186: steps: start 4 public replays at once. expected: 3 run; the 4th shows "Demo busy, try again in a minute."
- JRN-187: steps: simulate 24 h passing. expected: public replays are deleted with their events, except any with corrections or a saved note; practitioner replays are kept.
- JRN-188: steps: inspect the public replay API. expected: only that replay's frames/cues/path/counts; no keys or other attempts' data.
- JRN-189: steps: a route without a recording. expected: no Replay button; the replay URL shows "No demo recording yet."
- JRN-190: steps: re-run the earlier check scripts. expected: earlier behaviour is unchanged.
