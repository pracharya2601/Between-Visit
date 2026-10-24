# Phase 9 Requirements: Relevance Policy
Version: phase-9

Goal: plain backend code (never the LLM) decides what to speak. For each vision event on a running attempt it logs exactly one "cue" event, spoken or suppressed with a reason, and sends spoken cues through the existing cue path to GlassCam and the phone caption. No new UI. See ../overview.md. Phases 1–8 must keep working.

## Cue event
- REQ-284 [event] When a vision or vision_error event is logged on a running attempt, the system shall log exactly one "cue" event with text, priority, spoken, suppressed_reason, checkpoint, entity, route_version.
- REQ-285 [event] When a timer-detected condition fires (no frames / no usable result), the system shall log a "cue" event even without a vision event. (interpreted)
- REQ-286 [event] When a cue is spoken, the system shall deliver it through the existing guide path: pushed to GlassCam if live, plus phone caption polling (the phone speaks only if GlassCam isn't live and the toggle is on, as in Phase 5).
- REQ-287 [always] Cue text shall come only from fixed templates and practitioner-approved landmark text; LLM output is never spoken verbatim except entity labels. (interpreted)
- REQ-288 [state] While an attempt is paused, ended, not started, or a teach session, the system shall produce no cues.
- REQ-289 [always] The system shall show nothing new in the UI.

## Rule order (first match wins; then rule 5 applies to spoken cues)
### Rule 1: vision unavailable (priority 0)
- REQ-290 [event] When a vision result has unusable true, the system shall speak "Vision unavailable, please pause." (priority 0). (interpreted: immediate on an unusable frame, per the original rule)
- REQ-291 [state] While running with no frames (glasses or phone) for 2 s, the system shall speak "Vision unavailable, please pause." (priority 0).
- REQ-292 [state] While frames are arriving but there has been no usable vision result for 5 s (e.g. repeated vision_error), the system shall speak "Vision unavailable, please pause." (priority 0).
- REQ-293 [event] When a vision_error occurs and the 5 s condition isn't met, the system shall log a silent cue with suppressed_reason "vision_error".
- REQ-294 [unwanted] If the pause message was already sent and no usable frame has arrived since, then the system shall suppress it as "pause_already_sent".
- REQ-295 [event] When a usable vision result arrives, the system shall re-arm the pause message.
- REQ-296 [event] When vision stops at the 30-minute limit, the system shall speak "Vision unavailable, please pause." once. (interpreted)

### Rule 2: next checkpoint (priority 2)
- REQ-297 [event] When checkpoint_match equals the next checkpoint in order (the first one at the start), the system shall speak it once per checkpoint and advance "next".
- REQ-298 [always] Minimal cue style shall say "Checkpoint N: <name>." (N = 1-based order).
- REQ-299 [always] Standard cue style shall say "Checkpoint N: <name>. <landmark text>".
- REQ-300 [unwanted] If checkpoint_match is a checkpoint other than the next one, or one already spoken, then the system shall not cue it under rule 2 and shall continue to rule 3. (interpreted)

### Rule 3: new entity (priority 1)
- REQ-301 [always] Candidates shall be new_entities in the vision result; if several qualify, the system shall pick the nearest (depth, else distance band), then the highest confidence. (interpreted)
- REQ-302 [unwanted] If confidence < 0.6, then the system shall suppress it as "low_confidence".
- REQ-303 [unwanted] If the label matches a known entity of the pinned route version (case-insensitive), then the system shall suppress it as "known_entity".
- REQ-304 [unwanted] If no_repeat is on and the same label was cued within 3 m of the client's current position (or within 20 s when there's no pose), then the system shall suppress it as "duplicate".
- REQ-305 [state] While no_repeat is off, the duplicate rule shall be skipped.
- REQ-306 [always] Direction wording: ahead → "<Label> ahead", left → "<Label> on your left", right → "<Label> on your right".
- REQ-307 [always] Distance: use depth_centre for ahead, depth_left for left, depth_right for right, rounded to the nearest 0.5 m: ", about X metres." ("1 metre" singular, interpreted).
- REQ-308 [unwanted] If that side's depth is null, then the system shall use the distance band: near → ", close.", mid → ", a few steps.", far → ", further ahead."
- REQ-309 [always] Example: "Chair ahead, about 1.5 metres." The label is lower-cased and capitalised; person → "Person".

### Rule 4: on route
- REQ-310 [state] While "Stay silent while on route" is on, the system shall suppress as "on_route_silent".
- REQ-311 [state] While it's off and on_route is true, the system shall speak "On route." (priority 2) at most once every 20 s.
- REQ-312 [unwanted] If "On route." was spoken less than 20 s ago, or on_route is false, then the system shall log a silent cue "nothing_to_say". (interpreted for on_route false)

### Rule 5: rate limit
- REQ-313 [unwanted] If a non-zero-priority cue would be spoken less than 3 s after the last spoken cue, then the system shall suppress it as "rate_limited".
- REQ-314 [always] Priority 0 cues shall bypass the rate limit and shall count as the last spoken cue. (interpreted)
- REQ-315 [always] A rate-limited checkpoint cue shall not count as spoken, so it can fire on a later match; a rate-limited entity shall not count as cued for the duplicate rule. (interpreted)

## Quality requirements
```
Q-42 Tag: Policy.Determinism
     Scale: different cue outputs for the same input sequence across 3 replays
     Meter: unit-style replay of a fixed vision-event sequence
     Must: 0   Plan: 0
Q-43 Tag: Policy.Coverage
     Scale: vision events without exactly one cue event
     Meter: DB count on a simulated run
     Must: 0   Plan: 0
Q-44 Tag: Cue.Latency
     Scale: ms from vision event logged to guide pushed to GlassCam
     Meter: wss client, 5 trials
     Must: 500   Plan: 100
Q-45 Tag: Cue.Overload
     Scale: spoken non-0 cues within any 3 s window
     Meter: simulated busy run
     Must: ≤1   Plan: ≤1
```
