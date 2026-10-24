# Phase 6 Journeys
(Earlier journeys stay valid. Check data is deleted afterwards.)

- JRN-80: steps: open Routes. expected: no blank-named routes; the user's own routes untouched; the hidden test route has 0 checkpoints; "att-test" still works.
- JRN-81: steps: start a temporary attempt, stream 5 fps for 20 s. expected: at most about 20 vision calls (≤1/s); frames received ≈100; no backlog after the stream stops.
- JRN-82: steps: pause the attempt and keep streaming. expected: no new vision events while paused.
- JRN-83: steps: post the user's route checkpoint 2 photo as a frame. expected: a "vision" event with checkpoint_match = checkpoint 2's name, latency_ms reported, model "claude-haiku-4-5…", the route_version, no image bytes.
- JRN-84: steps: post a black frame. expected: a vision event with unusable true.
- JRN-85: steps: post a frame while the model is forced to time out or fail (e.g. a tiny timeout in a test). expected: a "vision_error" event; the next frame is analysed normally.
- JRN-86: steps: simulate 30 running minutes. expected: one "vision_stopped" event; no further vision calls.
- JRN-87: steps: GET /api/attempts/{id}/events, and an unknown id. expected: newest first, with no keys; unknown → 404.
- JRN-88: steps: change the model setting. expected: new vision events show the new model with no code change.
- JRN-89: steps: inspect DB/logs after the checks. expected: no frame bytes, no keys; the temporary attempt, exercise and events are deleted.
