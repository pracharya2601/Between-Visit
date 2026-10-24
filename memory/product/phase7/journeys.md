# Phase 7 Journeys
(Earlier journeys stay valid. Check data is deleted afterwards.)

- JRN-90: steps: over wss on a running temp attempt, send a phone line (ts 1000) then a valid 256×192 DPT1 frame (ts 1030) with left third 1.0 m, centre 2.5 m, right 5.0 m in the middle rows. expected: depth frame count +1; frames_received unchanged; /device-test shows depth 1.00 / 2.50 / 5.00 and the pose x, z, heading, tracking.
- JRN-91: steps: send a DPT1 frame with the wrong length. expected: dropped (depth_dropped +1); connection open; no vision call.
- JRN-92: steps: send a DPT1 frame with format 2, or width 0. expected: dropped; no crash.
- JRN-93: steps: send a DPT1 frame whose ts is 100 ms from any phone line. expected: dropped as unpaired; the depth summary is unchanged.
- JRN-94: steps: send a DPT1 frame where the right third is all zeros. expected: right depth null; left/centre computed.
- JRN-95: steps: stream 50 DPT1 frames with no JPEGs while running. expected: 0 vision events caused by them; nothing stored.
- JRN-96: steps: send a phone line with ar_planes, ar_points and an unknown field, then a bad ar_pose (10 floats). expected: extras ignored; the previous valid pose is kept.
- JRN-97: steps: send a JPEG frame with fresh phone + depth data. expected: the vision event contains position x/z, heading_deg, ar_tracking, depth left/centre/right; the prompt includes the depths as text.
- JRN-98: steps: let phone/depth go stale (>1 s), send a JPEG. expected: the vision event has those fields null; the prompt says "depth unavailable".
- JRN-99: steps: open the run page and its API; grep the logs. expected: no pose or depth values; no keys.
- JRN-100: steps: run wss_ingest_check.py and vision_check.py. expected: earlier behaviour is unchanged.
