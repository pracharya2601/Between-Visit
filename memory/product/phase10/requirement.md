# Phase 10 Requirements: Start-Grace Fix + Attempt Review
Version: phase-10

Goal: no spurious pause line at the start of a run, and a practitioner review page per attempt with stats, a readable timeline of what was said and silenced (and why), and the path in 3D or 2D, linked to the timeline. See ../overview.md. Phases 1–9 must keep working.

## Fix
- REQ-316 [state] While running after Start, the system shall not apply the 2 s "no frames" pause rule until the first frame (glasses or phone) arrives or 15 s have passed since Start.
- REQ-317 [always] A phone-camera run that starts its camera within 15 s shall hear no pause line at the start.
- REQ-318 [always] After Resume, the same grace shall apply until the next frame or 15 s. (interpreted)

## Data for review
- REQ-319 [always] Cue events shall also store pos_x and pos_z (from the vision event, or the newest phone line for timer cues; null if none).
- REQ-320 [always] Suppressed cue events shall store would_have_said (the text the rule would have spoken, when one exists) and detail fields used for plain-word reasons (e.g. seconds_since_last, metres_since_last, confidence).
- REQ-321 [state] While a run is running and has heading/steps from the phone, the system shall store a compact motion sample (t, heading, steps) on the attempt whenever steps change, practitioner-only, for the 2D fallback. (interpreted)

## Entry point
- REQ-322 [always] Each attempt on the client page shall have a "Review" link to /review/{attempt id} (practitioner side).
- REQ-323 [unwanted] If the attempt id is unknown, then the review page shall show "Attempt not found".
- REQ-324 [state] While the attempt is not_started, the review page shall show "This attempt hasn't started yet." (interpreted)

## Header
- REQ-325 [always] The header shall show the client display name, the route name and version ("v1"), and the date (local).
- REQ-326 [always] The header shall show elapsed time excluding pauses.
- REQ-327 [always] The header shall show checkpoints reached "n of N" (n = checkpoint cues actually spoken; N = checkpoints in the pinned version).
- REQ-328 [always] The header shall show the number of help requests.
- REQ-329 [always] The header shall show "Cues spoken: X · suppressed: Y" where Y excludes routine silences (on_route_silent, nothing_to_say).

## Timeline
- REQ-330 [always] Each item shall show the time from start (m:ss).
- REQ-331 [always] The timeline shall include start, pause, resume and end.
- REQ-332 [always] The timeline shall include checkpoints reached.
- REQ-333 [always] The timeline shall include spoken cues with their text.
- REQ-334 [always] The timeline shall include suppressed cues with the would-have-said text and the reason in plain words.
- REQ-335 [always] The timeline shall include help requests.
- REQ-336 [always] The timeline shall include practitioner messages.
- REQ-337 [always] The timeline shall include vision unavailable and uncertain moments.
- REQ-338 [always] Routine silences (on_route_silent, nothing_to_say) shall be hidden, with one line "N routine silences hidden".
- REQ-339 [always] Plain-word reasons: duplicate → "Not repeated: already said X s ago" (or "…X m ago"); rate_limited → "Held back: another cue X s earlier"; low_confidence → "Not sure enough (confidence 0.45)"; known_entity → "Already part of the route"; pause_already_sent → "Pause message already given"; vision_error → "Vision check failed". (interpreted)
- REQ-340 [always] The timeline shall have filters All / Spoken / Suppressed (aria-pressed buttons).
- REQ-341 [always] Each item with vision data shall have a "Details" toggle showing the raw vision JSON, collapsed by default.
- REQ-342 [always] The timeline list is the accessible alternative to the path view: semantic list, each item announces type, time, text and reason.

## Path
- REQ-343 [state] While the pinned route version has 3D memory, the review page shall reuse the 3D view (points, planes, ≤50k points) with the attempt trail as a line, checkpoint markers and a dot for each cue with a pose.
- REQ-344 [always] Spoken and suppressed cue dots shall use clearly different colours plus shape/legend (not colour alone).
- REQ-345 [always] In 3D, the run trail and cue positions shall be translated so the run's first trail point sits on the teach walk's first trail point.
- REQ-346 [state] While aligned, the page shall show under the path: "Run start aligned to the taught route's entrance."
- REQ-347 [state] While there's no 3D memory, the page shall draw a 2D top-down path (SVG): from the attempt's AR trail if present, otherwise dead reckoning from heading + steps samples (about 0.7 m per step, interpreted), with cue dots.
- REQ-348 [unwanted] If there's no trail and no heading/steps, then the path area shall show "No path recorded for this attempt."
- REQ-349 [event] When a cue dot is clicked (or activated by keyboard), the system shall highlight the matching timeline item and scroll to it.
- REQ-350 [event] When a timeline item with a dot is selected, the system shall highlight its dot in the path view.

## Demo data
- REQ-351 [always] The builder shall leave two finished demo attempts for Client A, both with the exercise goal "Review demo (synthetic)", with a mix of spoken and suppressed cues (including a duplicate, a rate-limited one, a low-confidence one, a help request and a practitioner message):
  - one on a simulated taught route with 3D memory ("Review demo route 3D (synthetic)");
  - one on a plain route without 3D memory using heading + steps only ("Review demo route 2D (synthetic)").
- REQ-352 [always] All other check data shall be deleted; leftover blobs shall be made unservable and reported.

## Quality requirements
```
Q-46 Tag: Review.Accuracy
     Scale: header counts that disagree with the timeline/event log
     Meter: compare on both demo attempts
     Must: 0   Plan: 0
Q-47 Tag: Review.Load
     Scale: seconds to show the header + timeline (3D can follow)
     Meter: headless timing
     Must: 3   Plan: 1.5
Q-48 Tag: Review.Understandable
     Scale: suppressed items a practitioner can't explain from the plain-word reason
     Meter: human
     Must: 0   Plan: 0
Q-49 Tag: Start.Grace
     Scale: pause lines in the first 15 s of a phone-camera run started within 5 s
     Meter: simulated run
     Must: 0   Plan: 0
```
