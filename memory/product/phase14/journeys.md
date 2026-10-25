# Phase 14 Journeys
(Earlier journeys stay valid except where superseded.)

- JRN-191: steps: open "/". expected: the exact headline, subline and research line with 2 working source links; 3 steps; "Try the demo" (primary) and "Open the practice workspace"; a link to /research; the footer. superseded: [JRN-6 home now at /workspace]
- JRN-192: steps: click "Open the practice workspace". expected: /workspace shows the practice, practitioner and clients; no "Device test" link; the logo returns to /workspace.
- JRN-193: steps: open /research. expected: the CDC, ACVREP and Dove et al. entries with exact numbers, quotes and links; "Still validating with practitioners" with an empty list.
- JRN-194: steps: open Routes. expected: "Entrance → hallway turn → reception desk (synthetic)" and "Lobby to elevator (synthetic)"; no old names.
- JRN-195: steps: open the renamed 3D route's version history, its review (att-iiri) and memory endpoint for v1 and v2. expected: checkpoints Entrance / Hallway turn / Reception desk everywhere; past cue texts read "Checkpoint 1: Entrance." etc.; no old checkpoint names in the DB for this route.
- JRN-196: steps: check the nav on every workspace page. expected: no "Device test"; /device-test still works directly.
- JRN-197: steps: run axe on every page; tab through each. expected: 0 serious/critical; one h1; logical headings; visible focus in visual order; a working skip link; unique titles.
- JRN-198: steps: grep the UI copy. expected: no safety/obstacle-avoidance claims; the footer is verbatim on every page.
- JRN-199: steps: in a fresh private context: "/" → Try the demo → On v1 → Start replay → wait for the end → review link. expected: works with no stored state; the chair is spoken on v1 with the new checkpoint names.
- JRN-200: steps: re-run the earlier check scripts. expected: all pass.
