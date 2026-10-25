# Phase 11 Journeys
(Earlier journeys stay valid except where superseded. Keep both demo attempts; delete everything else.)

- JRN-149: steps: replay "On route." then an object cue 1 s later. expected: the object cue is spoken (not rate-limited). superseded: [] (refines JRN-130/131)
- JRN-150: steps: replay a checkpoint cue held back by the limit, then a result that doesn't match it. expected: the checkpoint cue is spoken on that next result.
- JRN-151: steps: replay a held-back chair, then a result without the chair; separately, a result with the chair at a new depth. expected: no retry without the chair; with the chair → spoken with the new distance.
- JRN-152: steps: open a review with a vision failure. expected: "Vision check failed (stayed silent)"; no "Would have said: No cue" anywhere.
- JRN-153: steps: on the 3D demo review, find the chair item and press Confirm. expected: "Saved to route memory as v2"; the buttons are replaced; the route history shows "v2: chair confirmed by J. Rivera (synthetic), HH:MM"; a correction is saved with new_route_version 2; v1 is unchanged.
- JRN-154: steps: look at the 3D view of the demo review. expected: a labelled "chair" marker at the confirmed position, in the legend, distinct from cue dots.
- JRN-155: steps: press New attempt on the 3D demo exercise and replay the same simulated run. expected: the new attempt shows v2; the old attempts still show v1; the chair is suppressed with "Known: chair confirmed in v2".
- JRN-156: steps: replay a chair 4 m from the confirmed one in another segment. expected: not known → spoken (subject to the other rules).
- JRN-157: steps: on an object item press Edit, change the label to "bench" and the side to left, confirm. expected: the next version has "bench" (left); the correction records before/after.
- JRN-158: steps: Dismiss an object item. expected: "Dismissed"; a correction with action dismiss and no new version.
- JRN-159: steps: try to correct an already-corrected item via the API. expected: 409.
- JRN-160: steps: in the version history press "Remove from memory" on the bench. expected: a new version without it; the history line "vN: bench removed by J. Rivera (synthetic), HH:MM"; earlier versions are unchanged.
- JRN-161: steps: open the 2D demo review and Confirm an object without depth. expected: saved with a segment and no position; matching on a later run uses the segment.
- JRN-162: steps: re-run the earlier check scripts. expected: earlier behaviour is unchanged.
