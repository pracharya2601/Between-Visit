# Phase 22 journeys

- JRN-22-1: A run starts on a scan route. Checkpoint 1 is logged at the start as "Reached by position". Being within 1.5 m of checkpoint 2 then reaches checkpoint 2.
- JRN-22-2: A run starts on a teach-walk or photo route. Behaviour is the same as before (all existing policy cases still pass).
- JRN-22-3: The demo story is unchanged: v1 speaks the chair, v2 holds it back as known, and checkpoints go Entrance, then Hallway turn, then Reception desk.
- JRN-22-4: With the setting at its default, /demo, /api/demo/scene and /api/demo/points give the same output as before.
- JRN-22-5: A team member sets the synthetic route through the button or setting, then resets it. /demo still works both ways, and the setting is left on the synthetic demo.
- JRN-22-6: The setting points to a route with nothing usable, or one that is missing something. The site falls back to the synthetic demo exactly as today.
- JRN-22-7: The "Use as website demo" button appears only on routes with a ready real recording.
