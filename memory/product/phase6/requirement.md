# Phase 6 Requirements: Vision Analysis (no speaking)
Version: phase-6

Goal: while an attempt runs, the server analyses the newest frame from GlassCam or the phone at most once per second with Claude Haiku 4.5, against the pinned route memory. It logs a structured result per call and stores no frames. Nothing is spoken (that's Phase 7). See ../overview.md. Phases 1–5 must keep working.

## Cleanup
- REQ-180 [event] When this phase deploys, the system shall delete the two blank-named routes with ids b970d705-4f36-43ed-9163-d2e42bf5ea2e and a5ffedc8-237a-473e-92dd-4642d82fa68e (only those ids; never routes the user creates).
- REQ-181 [event] When this phase deploys, the system shall delete the empty checkpoint on the hidden "Test route (synthetic)". "att-test" stays working.

## Frame selection
- REQ-182 [state] While an attempt is running, the system shall accept frames for analysis from GlassCam (WS) and the phone (POST).
- REQ-183 [state] While an attempt is paused, ended or not started, the system shall analyse no frames.
- REQ-184 [always] The system shall analyse only the newest frame, at most one per second per attempt.
- REQ-185 [state] While a vision call is in progress for an attempt, the system shall skip (discard) new frames for analysis; there's no queue.
- REQ-186 [always] The system shall keep at most one frame in memory per attempt, overwritten by newer ones, and discard it after the call. Frames are never stored.
- REQ-187 [always] Frame counting from Phases 2 and 5 shall continue unchanged for every frame, including skipped ones.

## Vision call
- REQ-188 [always] The system shall call Claude vision via the Emergent LLM key with the model from a single config setting (default Claude Haiku 4.5).
- REQ-189 [always] The prompt shall include the frame and the pinned route version's memory as text: checkpoints in order (name, landmark text), known entities (label, relation, verified) and the last matched checkpoint.
- REQ-190 [always] The last matched checkpoint shall be the most recent non-null checkpoint_match in this attempt's vision events (null at start). (interpreted)
- REQ-191 [always] The prompt shall require JSON only: {"checkpoint_match": name|null, "on_route": bool, "new_entities": [{"label","relation":"left|right|ahead","distance_band":"near|mid|far","confidence":0-1}], "uncertain": bool, "unusable": bool}.
- REQ-192 [always] The prompt shall define unusable as dark, blank, covered or too blurred.
- REQ-193 [always] The prompt shall limit new_entities to objects that matter for walking (e.g. chair, cart, sign stand, open door).
- REQ-194 [always] The prompt shall label any person "person" with no description.
- REQ-195 [unwanted] If the reply isn't valid JSON matching the schema, then the system shall log "vision_error" with reason "bad_json". (interpreted)
- REQ-196 [unwanted] If checkpoint_match isn't a name in the pinned version, then the system shall store it as null and set uncertain true. (interpreted)
- REQ-197 [unwanted] If an entity has a description beyond "person" for a person, then the system shall strip it to label "person". (interpreted)

## Logging
- REQ-198 [event] When a vision call succeeds, the system shall log an attempt_event type "vision" with the result JSON, latency_ms, model, route_version, frame source (glasses|phone, interpreted), checkpoint = checkpoint_match, uncertain, spoken false.
- REQ-199 [unwanted] If the call fails or takes more than 8 s, then the system shall log "vision_error" (reason, latency_ms, model) and carry on with the next frame.
- REQ-200 [state] While an attempt has been running for more than 30 minutes (paused time excluded), the system shall analyse no more frames.
- REQ-201 [event] When the 30-minute limit is reached, the system shall log one "vision_stopped" event with reason "time_limit". (interpreted)
- REQ-202 [always] No event shall contain image bytes or base64.

## Events API
- REQ-203 [event] When GET /api/attempts/{id}/events is called, the system shall return that attempt's events newest first.
- REQ-204 [unwanted] If the attempt id is unknown, then the system shall return 404.
- REQ-205 [always] The events response shall never include keys or key hashes. Access is practitioner-side with no login, the same as the other practitioner endpoints. (interpreted)

## Check (once the user's route is ready)
- REQ-206 [event] DEFERRED by the user: the checkpoint-2 match check runs in a later step, once a route is created automatically from a GlassCam walk. When the user's route is saved, the builder shall create a temporary attempt on it, post checkpoint 2's photo as a frame, confirm the vision event's checkpoint_match is checkpoint 2, report latency_ms, then delete the temporary exercise, attempt and events.

## Quality requirements
```
Q-27 Tag: Vision.Latency
     Scale: latency_ms per vision call
     Meter: vision events over the check + 10 calls
     Must: 8000   Plan: 2500 (estimate)
Q-28 Tag: Vision.Accuracy
     Scale: checkpoint photo posted as a frame matched to the right checkpoint
     Meter: the user's route, checkpoint 2 photo (+ others if time allows)
     Must: checkpoint 2 matches   Plan: all match
Q-29 Tag: Vision.Rate
     Scale: vision calls per attempt per second at 5 fps input
     Meter: 20 s of 5 fps frames
     Must: ≤1   Plan: ≤1, with no backlog after the frames stop
Q-30 Tag: Privacy.Frames
     Scale: frame bytes in DB, disk or logs
     Meter: inspection
     Must: 0   Plan: 0
Q-31 Tag: Cost.Cap
     Scale: vision calls after 30 running minutes
     Meter: simulated clock/test
     Must: 0   Plan: 0
```
