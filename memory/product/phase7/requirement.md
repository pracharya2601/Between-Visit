# Phase 7 Requirements: Phone Sensors from GlassCam (depth + pose)
Version: phase-7

Goal: the same ingest socket accepts LiDAR depth frames and AR phone-state lines from the GlassCam app. Depth is reduced to three distances (left/centre/right), pose and heading are kept as the newest values, and both enrich vision events and the Claude prompt. Depth is never treated as an image. See ../overview.md. Phases 1–6 must keep working.

## Depth frames ("DPT1")
- REQ-207 [event] When a binary message starts with the 4 bytes "DPT1", the system shall treat it as LiDAR depth, never as a picture.
- REQ-208 [always] A depth message shall never be sent to vision, decoded as an image, put in the newest-frame slot, or stored.
- REQ-209 [always] The system shall parse the 36-byte little-endian header: width u16 @4, height u16 @6, ts_capture_ms f64 @8, fx f32 @16, fy f32 @20, cx f32 @24, cy f32 @28, format u8 @32.
- REQ-210 [always] The body shall be width×height u16 depths in mm, row-major; 0 = no reading.
- REQ-211 [unwanted] If the length isn't 36 + 2×width×height, then the system shall drop the message and increment depth_dropped. (counter interpreted)
- REQ-212 [unwanted] If format isn't 1 (millimetres), or width/height is 0, then the system shall drop the message and increment depth_dropped. (interpreted)
- REQ-213 [event] When a valid depth frame arrives, the system shall increment depth_frames_received (separate from frames_received). Depth frames don't count as picture frames.
- REQ-214 [always] Depth frames over the 1 MB limit shall be dropped as depth_dropped, keeping the connection open. (interpreted)

## Phone lines
- REQ-215 [event] When a text message {"type":"phone",…} arrives, the system shall keep the newest values per stream for ar_tracking, ar_pose (16 floats, column-major), heading_deg, has_lidar and ts_capture_ms.
- REQ-216 [always] Position shall be ar_pose elements 12, 13 and 14 (x, y, z) in metres; +Y up, −Z north. Events use x and z.
- REQ-217 [always] The system shall ignore ar_planes, ar_points and unknown fields.
- REQ-218 [unwanted] If ar_pose isn't 16 numbers, or a field has the wrong type, then the system shall ignore that field and keep the previous value. (interpreted)
- REQ-219 [always] The system shall keep recent phone lines (about the last 1 s) in memory only, for pairing. (interpreted)
- REQ-220 [always] Phone lines shall not be treated as "motion" messages and shall not pair with picture frames. (interpreted)

## Pairing & depth summary
- REQ-221 [event] When a valid depth frame arrives, the system shall pair it with the phone line whose ts_capture_ms is closest and within ±60 ms.
- REQ-222 [unwanted] If no phone line is within ±60 ms, then the system shall drop the depth frame and increment depth_unpaired. (counter interpreted)
- REQ-223 [event] When a depth frame is paired, the system shall compute, over the middle third of rows (interpreted), the median of non-zero depths in metres for the left, centre and right thirds of columns.
- REQ-224 [unwanted] If a third has no non-zero readings, then the system shall set that value to null.
- REQ-225 [always] The system shall keep only the newest depth summary (left/centre/right, ts) per stream and discard the raw depth array immediately.

## Vision enrichment
- REQ-226 [event] When a vision event is logged, the system shall add position x, position z, heading_deg and ar_tracking from the newest phone line.
- REQ-227 [event] When a vision event is logged, the system shall add depth left/centre/right from the newest depth summary.
- REQ-228 [unwanted] If the newest phone line or depth summary is older than 1 s at analysis time, then the system shall set those fields to null. (interpreted)
- REQ-229 [always] The Claude prompt shall include the depth left/centre/right in metres as text, with an instruction to use them for distance_band (e.g. near < 1.5 m, mid 1.5–4 m, far > 4 m, interpreted).
- REQ-230 [state] While no depth is available, the prompt shall say "depth unavailable" and distance_band is estimated from the image.

## Display & privacy
- REQ-231 [always] /device-test shall show phone pose x, z (m, 2 dp), heading (°), tracking state, depth left/centre/right (m) and a separate depth-frame count (plus dropped/unpaired).
- REQ-232 [always] Pose and depth shall appear only in vision events, the practitioner events API and the /device-test status; never on the client run page or in its API, never in logs.
- REQ-233 [always] Picture frames, motion pairing, vision rate limit, cues and existing counters shall behave as before.

## Quality requirements
```
Q-32 Tag: Safety.DepthNotImage
     Scale: DPT1 messages reaching vision or the image slot
     Meter: send 50 depth frames while running; count vision calls attributable to them
     Must: 0   Plan: 0
Q-33 Tag: Depth.Accuracy
     Scale: |computed − expected| median per third on a synthetic frame with known values
     Meter: crafted DPT1 frames
     Must: 0.01 m   Plan: exact
Q-34 Tag: Depth.Throughput
     Scale: ms of server CPU per 256×192 depth frame
     Meter: timing over 100 frames
     Must: 20   Plan: 5 (estimate)
Q-35 Tag: Privacy.Pose
     Scale: pose/depth values in public (run page) responses or logs
     Meter: inspection
     Must: 0   Plan: 0
```
