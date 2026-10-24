# Phase 9 Journeys
(Earlier journeys stay valid. Check data is deleted afterwards. A fake vision results injector or replay hook is allowed for checks so the rules can be checked deterministically.)

- JRN-117: steps: replay a vision result with unusable true on a running attempt. expected: a cue "Vision unavailable, please pause." priority 0, spoken; GlassCam receives a guide with priority 0.
- JRN-118: steps: another unusable result right after. expected: a silent cue "pause_already_sent"; after a usable result, a later unusable one speaks again.
- JRN-119: steps: stop all frames for 2 s while running. expected: one spoken pause cue (no vision event needed).
- JRN-120: steps: frames arriving but vision_error for 5 s. expected: each error → a silent "vision_error" cue; at 5 s, one spoken pause cue.
- JRN-121: steps: checkpoint_match = checkpoint 1, Minimal style. expected: "Checkpoint 1: <name>." priority 2; the same match again → not re-spoken (falls through to later rules).
- JRN-122: steps: Standard style, match checkpoint 2 after 1. expected: "Checkpoint 2: <name>. <landmark text>"; matching checkpoint 3 before 2 → no checkpoint cue.
- JRN-123: steps: new entity chair, ahead, confidence 0.8, depth_centre 1.4. expected: "Chair ahead, about 1.5 metres." priority 1.
- JRN-124: steps: entity "cart", right, depth_right null, band mid. expected: "Cart on your right, a few steps."
- JRN-125: steps: entity confidence 0.5. expected: silent "low_confidence".
- JRN-126: steps: an entity whose label is in the version's known_entities. expected: silent "known_entity".
- JRN-127: steps: chair cued, then chair again after moving 2 m (no_repeat on). expected: silent "duplicate"; after moving 4 m → spoken; with no pose: duplicate within 20 s, spoken after.
- JRN-128: steps: the same as JRN-127 with no_repeat off. expected: spoken again (subject to the 3 s rate limit).
- JRN-129: steps: nothing applies, stay-silent on. expected: silent "on_route_silent".
- JRN-130: steps: nothing applies, stay-silent off, on_route true, results every 1 s for 25 s. expected: "On route." spoken at t≈0 and t≈20 s; the others silent "nothing_to_say".
- JRN-131: steps: an entity cue, then a checkpoint cue 1 s later. expected: the second is silent "rate_limited"; the checkpoint is spoken on its next match after 3 s.
- JRN-132: steps: a pause cue 1 s after a spoken cue. expected: spoken (priority 0 bypasses the limit).
- JRN-133: steps: count events on a simulated run. expected: every vision/vision_error event has exactly one cue event; no cues while paused or on teach streams; no new UI.
- JRN-134: steps: re-run the earlier check scripts. expected: earlier behaviour is unchanged.
