# Phase 10 Journeys
(Earlier journeys stay valid except where superseded. Check data is deleted except the two demo attempts.)

- JRN-135: steps: Start a run, send no frames for 10 s, then start phone frames. expected: no pause cue before the first frame; normal rules after it. superseded: [JRN-119 only for the first 15 s after Start]
- JRN-136: steps: Start a run, send no frames at all for 16 s. expected: one pause cue at about 15–17 s.
- JRN-137: steps: on Client A's page, find a "Review" link on each attempt and open the 3D demo. expected: the header shows Client A (synthetic), "Review demo route 3D (synthetic) · v1", the date, elapsed time excluding pauses, "Checkpoints reached n of N", the help count, "Cues spoken: X · suppressed: Y".
- JRN-138: steps: compare the header counts with the timeline. expected: they match; Y excludes routine silences; "N routine silences hidden" is shown.
- JRN-139: steps: read the timeline. expected: start/pause/resume/end, checkpoint reached, spoken cue text, suppressed items with would-have-said text and reasons such as "Not repeated: already said 8 s ago", "Held back: another cue 1 s earlier", "Not sure enough (confidence 0.45)", a help request, a practitioner message, a vision unavailable or uncertain item.
- JRN-140: steps: use the filters Spoken, then Suppressed, then All. expected: the list filters correctly; the buttons show their pressed state.
- JRN-141: steps: open "Details" on a cue item. expected: the raw vision JSON is shown; collapsed by default.
- JRN-142: steps: look at the 3D path. expected: points, planes, the run trail line, checkpoint markers, cue dots in two styles with a legend; the note "Run start aligned to the taught route's entrance."
- JRN-143: steps: click a cue dot. expected: the matching timeline item is highlighted and scrolled into view; selecting a timeline item highlights its dot.
- JRN-144: steps: open the 2D demo. expected: a top-down SVG path from heading + steps with cue dots and the same linking; no 3D view.
- JRN-145: steps: open the review for an attempt with no path data, a not-started attempt, and /review/nope. expected: "No path recorded for this attempt.", "This attempt hasn't started yet.", "Attempt not found".
- JRN-146: steps: use the review page with keyboard/screen reader only. expected: the timeline gives every item's time, type, text and reason; filters and Details are operable.
- JRN-147: steps: open the run page/API for the demo attempts. expected: no trail, pose or review data is exposed to the client.
- JRN-148: steps: re-run the earlier check scripts. expected: earlier behaviour is unchanged (allowing for the start-grace change).
