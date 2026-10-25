# Phase 15 Journeys
(Earlier journeys stay valid except where superseded.)

- JRN-201: steps: Try the demo → On v1 → Start replay at 1920×1080. expected: the 3D view takes ~60% of the width with the frame smaller beside it; the caption, counts and labels "Synthetic demo (AI-generated images)" + "Synthetic 3D model" are visible with no scroll. superseded: [JRN-182 2D path → 3D]
- JRN-202: steps: watch the replay. expected: the trail grows; the "now" marker with a heading arrow walks down the corridor centre and turns right at the Hallway turn; the camera follows smoothly from behind/above; cue dots appear (amber spoken, grey held back).
- JRN-203: steps: look at the model. expected: floor, both walls, a left handrail, a yellow tactile strip, a reception desk at the end, a chair against the right wall near the chair cue; ~40k scan-like coloured points; numbered markers 1–3 at Entrance, Hallway turn, Reception desk.
- JRN-204: steps: toggle "Free look", orbit and zoom, toggle back. expected: follow stops, then resumes.
- JRN-205: steps: emulate prefers-reduced-motion. expected: a fixed overview of the whole route; no camera motion; markers still update.
- JRN-206: steps: replay On latest version (v2). expected: a purple "chair" triangle at the model's chair; the chair cue is held back as "Known: chair confirmed in v2" (2 of 2); v1 still speaks it (2 of 2).
- JRN-207: steps: open the review link after the replay. expected: the same 3D model with the full trail, cue dots, the chair triangle (v2) and checkpoint markers; clicking a dot highlights its timeline item.
- JRN-208: steps: open the existing review att-iiri. expected: shows the new synthetic model.
- JRN-209: steps: open the memory endpoint / machine view for v2. expected: the chair has a position.
- JRN-210: steps: open a review/replay with no 3D memory (the Lobby to elevator route). expected: the 2D fallback.
- JRN-211: steps: use a screen reader on the replay screen. expected: the text summary updates; the canvas has an aria-label.
- JRN-212: steps: re-run the earlier check scripts. expected: all pass.
