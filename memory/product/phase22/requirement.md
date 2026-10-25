# Phase 22: Scan entrance at start and choosing the website demo route

Approved by Prakash after the freeze. Do NOT create runs or data on "Downstair room". Change nothing else.

## 1. Scan routes: Entrance reached at run start (cue_policy.py / cue_runner.py)
- On routes whose route memory kind is "scan", checkpoint 1 (the Entrance, at the run start, 0,0,0) counts as reached when the run starts.
- It is logged as a normal checkpoint event with the reason "Reached by position". Position checking then moves straight on to checkpoint 2.
- Teach-walk and photo routes are unchanged. Alignment, the 3 m picture guard, the skip rule and the 1.5 m scan radius are unchanged.

## 2. Website demo route as a stored setting (backend/replay.py and the route replay page)
- `demo_route()` reads a stored setting. The default is the current synthetic demo route (the DEMO_ROUTE name), so nothing changes until the setting is set.
- Route replay page, team only: a "Use as website demo" button, shown only when that route has a ready real recording. Also a "Back to the synthetic demo" button.
- When the setting points to a route with a ready real recording, `/demo`, `/api/demo/scene` and `/api/demo/points` use that route:
  - its saved 3D model (scan)
  - its latest real recording (poses and frames)
  - its checkpoints
  - the chair from its latest version, if confirmed
  - its latest ended non-replay run for the review rows
- If anything is missing, fall back to the synthetic demo exactly as it works today.
- Landing copy stays as it is. If the chosen route has no confirmed chair, the v1/v2 strip and the hero card use the synthetic text.

## Checks
- Use the synthetic route only: switch the setting to it and back. Leave the setting on the synthetic demo.
- Do not run the full test suite. Targeted checks only.
