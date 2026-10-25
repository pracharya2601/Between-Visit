# Phase 17 Requirements: Checkpoint Detection Improvements
Version: phase-17

Goal: fewer false pauses and more reliable checkpoint progress, from the real test run ("My room", attempt c5779642…). Changes are in backend/cue_policy.py (decide, _usable) and the review wording. Phases 1–16 must keep working. Note: "My room" has no checkpoint positions (builder-made), so rule 2 doesn't apply to it; it applies to routes taught by walking.

## 1. Unusable frames
- REQ-547 [event] When a vision result has unusable true, the system shall log a silent cue with suppressed_reason "unusable_frame" and not pause. superseded: REQ-290
- REQ-548 [state] While frames are arriving but there has been no USABLE result for NO_USABLE_S (5 s), counting both unusable results and vision_error, the system shall speak "Vision unavailable, please pause." (p0) once, with the existing pause_already_sent / re-arm logic.
- REQ-549 [always] The no-frames rules (2 s after the first frame, 15 s start/resume grace) stay unchanged.

## 2. Position as a second signal
- REQ-550 [state] While the attempt's route version has a position for the NEXT checkpoint (the same source as checkpoint_positions for the replay) and the current pose is fresh (<1 s), the system shall align the pose like build_path (run start = route start).
- REQ-551 [event] When the aligned pose is within 1.0 m (x/z) of the next checkpoint's position, the system shall count it as reached even without a picture match.
- REQ-552 [always] A position-reached checkpoint shall be spoken exactly like a picture match (same text, priority, rate limit, held-back retry) with details {"by": "position"}.
- REQ-553 [always] Picture-matched checkpoints shall get details {"by": "picture"}.
- REQ-554 [state] While the version has no checkpoint positions or the pose is stale/missing, rule 2 shall not apply.

## 3. Skip one
- REQ-555 [always] Precedence: reaching the NEXT checkpoint (by picture or position) is evaluated before a skip. (interpreted)
- REQ-556 [event] When the picture matches the checkpoint AFTER the next one (next+1), the system shall speak next+1, advance past it, and log the skipped checkpoint as a silent cue with suppressed_reason "checkpoint_skipped" (details: skipped order/name, matched order/name).
- REQ-557 [always] Only one checkpoint can be skipped per decision (a match on next+2 or further does nothing); separate skips can happen later. (interpreted)
- REQ-558 [always] Progress never goes backwards; matches on earlier checkpoints are ignored for progress.
- REQ-559 [always] Skipped checkpoints don't count as reached in the review header; the progress-note fact sheet lists them as missed. (interpreted)

## 4. Review wording
- REQ-560 [always] Checkpoint items shall read "Reached by picture" or "Reached by position".
- REQ-561 [always] Skipped items shall read "Missed checkpoint N: name (moved on when N+1 matched)".
- REQ-562 [always] unusable_frame shall read "Blurry frame, ignored" and count as a routine silence (hidden, included in "N routine silences hidden", excluded from "suppressed").

## Checks
- REQ-563 [always] Add policy replay cases for all four rules to tests/cue_policy_check.py (3× determinism).
- REQ-564 [always] Read-only re-evaluation: re-run the "My room" attempt c5779642… logged vision results through the new policy WITHOUT writing anything, and report the old vs new pauses and checkpoints reached/missed.
- REQ-565 [always] The demo story still holds after the changes: v1 chair spoken 2/2, v2 held back 2/2, checkpoints progress Entrance → Hallway turn → Reception desk (by picture or position).

## Quality requirements
```
Q-75 Tag: Policy.FalsePause
     Scale: pause lines caused by a single unusable result
     Meter: replays + the My room re-evaluation
     Must: 0   Plan: 0
Q-76 Tag: Policy.Progress
     Scale: checkpoints reached in the My room re-evaluation (no positions available)
     Meter: re-evaluation
     Must: ≥ the old result   Plan: report
Q-77 Tag: Policy.Determinism
     Scale: differing outputs across 3 replays
     Meter: replay set
     Must: 0   Plan: 0
```
