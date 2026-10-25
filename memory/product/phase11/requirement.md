# Phase 11 Requirements: Fixes + Corrections & Route Memory Versions
Version: phase-11

Goal: practitioners turn review findings into route memory. Confirmed objects become known entities in a new route version (removable later, history never rewritten), new attempts use the latest version, and the cue policy stops announcing what's already known. Plus two policy/timeline fixes. See ../overview.md. Phases 1–10 must keep working; both demo attempts are kept.

## Fixes
- REQ-353 [always] A spoken "On route." shall not count as the last spoken cue for the 3 s limit and shall never cause another cue to be rate-limited.
- REQ-354 [unwanted] If a real cue was spoken less than 3 s ago, then "On route." shall be skipped as "nothing_to_say" (no talking over). (interpreted)
- REQ-355 [event] When a checkpoint cue is held back by the rate limit, the system shall retry it on the next result even if it isn't matched again, while that checkpoint is still the next one.
- REQ-356 [event] When an object cue is held back, the system shall retry it on the next result only if that result still sees the object (same label and side), using the new distance and re-checking the known/duplicate rules.
- REQ-357 [always] A vision failure shall show on the timeline as "Vision check failed (stayed silent)", never "Would have said: No cue".
- REQ-358 [always] The review timeline shall never show "Would have said:" when there's no would-have-said text. (interpreted)

## Attempt versions
- REQ-359 [always] Every attempt shall store its own route_version. superseded: the exercise-level pin from Phase 4 (JRN-56).
- REQ-360 [event] When an attempt is created (assignment or "New attempt"), the system shall set its route_version to the route's latest version.
- REQ-361 [always] Existing attempts shall keep their version; existing data is migrated by copying the exercise's pinned version onto its attempts. (interpreted)
- REQ-362 [always] The run page, vision prompt, cue policy and review shall use the attempt's route_version.
- REQ-363 [always] The client page shall show each attempt's version (e.g. "v2").

## Corrections on the review page
- REQ-364 [always] Every timeline item about an object (spoken or suppressed, i.e. with an entity) shall show Confirm, Edit and Dismiss.
- REQ-365 [event] When Confirm is pressed, the system shall add a known entity to the route memory: label, side (left|right|ahead), checkpoint segment, position, verified_by "J. Rivera (synthetic)", verified_at.
- REQ-366 [always] Segment = the stretch between the last checkpoint reached before the event and the next one (e.g. {from: 1, to: 2}; before the first checkpoint → {from: 0, to: 1}).
- REQ-367 [always] Position shall be start-relative (run start = origin): the client's pos + the depth distance along heading (ahead 0°, left −25°, right +25°, interpreted). Null if no pose or no depth for that side.
- REQ-368 [event] When Confirm saves, the system shall create the next route version (copying the route's LATEST version, not the attempt's) with the entity added, author J. Rivera (synthetic), created_at, and a change note "chair confirmed".
- REQ-369 [event] When Confirm succeeds, the item shall show "Saved to route memory as vN" and the buttons shall be replaced by that status.
- REQ-370 [event] When Edit is pressed, the system shall let the practitioner change the label (non-empty, ≤40 chars, interpreted) or side, then confirm with the edited values.
- REQ-371 [event] When Dismiss is pressed, the system shall log the correction with no new version and show "Dismissed" on the item.
- REQ-372 [always] Every action shall save a correction {attempt_event_id, action confirm|edit|dismiss, author, created_at, new_route_version (null for dismiss), label/side before and after}.
- REQ-373 [unwanted] If an item already has a correction, then the system shall reject another (409) and show its status. (interpreted)

## Version history
- REQ-374 [always] The route page and review page shall show a version history, newest first, e.g. "v2: chair confirmed by J. Rivera (synthetic), 14:32" (also "v1: route saved…", "v3: chair removed…", builder saves "checkpoints edited").
- REQ-375 [always] The version history shall list the current known entities with a "Remove from memory" button each.
- REQ-376 [event] When "Remove from memory" is pressed (with confirm), the system shall create the next version without that entity, change note "chair removed".
- REQ-377 [always] Route versions shall never be modified or deleted (history never rewritten).
- REQ-378 [always] Builder saves shall carry known entities and 3D memory forward to the new version. (interpreted)

## Views
- REQ-379 [always] The 3D and 2D review views shall show the known entities of the attempt's version as labelled markers, distinct from cue dots, and in the legend.
- REQ-380 [always] In 3D, entity positions shall use the same start alignment as the run trail.
- REQ-381 [unwanted] If an entity has no position, then it shall be listed in the history but not drawn. (interpreted)

## Policy
- REQ-382 [unwanted] If a new entity's label matches a known entity (case-insensitive) and both have positions within 2 m (start-relative), then the system shall suppress it as "known_entity".
- REQ-383 [unwanted] If either side has no position and the label matches a known entity in the same checkpoint segment, then the system shall suppress it as "known_entity".
- REQ-384 [always] The known_entity reason shall read "Known: chair confirmed in v2".
- REQ-385 [always] Known entities shall be included in the route memory text sent to Claude, as before.

## Quality requirements
```
Q-50 Tag: Memory.Integrity
     Scale: route_versions modified after creation
     Meter: snapshot compare after confirm/remove/builder save
     Must: 0   Plan: 0
Q-51 Tag: Memory.Effect
     Scale: confirmed chair spoken on the next simulated run with the same path
     Meter: the 3D demo check
     Must: 0   Plan: 0
Q-52 Tag: Memory.Precision
     Scale: chairs >2 m from the confirmed one (or in another segment) wrongly suppressed
     Meter: replay case
     Must: 0   Plan: 0
Q-53 Tag: Review.Clarity
     Scale: practitioner can tell what each correction did from the item + history
     Meter: human
     Must: yes   Plan: yes
```
