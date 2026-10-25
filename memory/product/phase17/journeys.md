# Phase 17 Journeys
- JRN-223: steps: replay one unusable result among usable ones. expected: a silent "unusable_frame", no pause. superseded: [JRN-117]
- JRN-224: steps: replay frames arriving with only unusable/vision_error results for 5 s. expected: one pause line; repeats → pause_already_sent; a usable result re-arms it.
- JRN-225: steps: replay a fresh pose within 0.8 m of the next checkpoint's position with no picture match. expected: the checkpoint is spoken, details {"by":"position"}; at 1.2 m → not reached.
- JRN-226: steps: the same with a stale pose (>1 s) or a version without positions. expected: not reached by position.
- JRN-227: steps: replay a picture match on next+1. expected: next+1 is spoken {"by":"picture"}; the skipped one is logged as silent "checkpoint_skipped"; next+2 matches do nothing; earlier matches never move progress back.
- JRN-228: steps: open a review with these events. expected: "Reached by picture" / "Reached by position", "Missed checkpoint 3: … (moved on when 4 matched)", "Blurry frame, ignored" hidden among routine silences; the header counts exclude missed ones.
- JRN-229: steps: a read-only re-evaluation of the My room attempt. expected: a report of old vs new pauses and checkpoints; no DB writes.
- JRN-230: steps: demo replays on v1 and v2 (2 each). expected: the chair story holds; checkpoints progress in order.
