# Phase 5 Journeys
(Earlier journeys stay valid except where superseded. Check data must be deleted afterwards.)

- JRN-62: steps: open Routes, query the DB. expected: no "Reception route (synthetic)" or "Unsaved draft (synthetic)"; no exercises/attempts/events for them; their photos 404.
- JRN-63: steps: open a valid run link at 390px. expected: one column; large buttons Start, Pause/Resume, Repeat cue, Request help, End; the summary shows goal, ordered checkpoint names and the stop rule; stream ID + key with copy buttons; elapsed, heading, steps; caption area aria-live="assertive"; no horizontal scroll.
- JRN-64: steps: tap Start. expected: the motion permission request happens in the same tap (iOS); status running; started_at set; a "start" event is logged; elapsed starts counting.
- JRN-65: steps: Pause, then Resume. expected: status paused then running; "pause" and "resume" events logged; elapsed doesn't count while paused.
- JRN-66: steps: tap End, confirm. expected: status ended, ended_at set, an "end" event; the page shows "This run has ended"; all controls are disabled; a Start API call returns 409.
- JRN-67: steps: call the run API with a wrong or missing X-Stream-Key. expected: 401; nothing changes.
- JRN-68: steps: while running, the practitioner types "Stay where you are, I'm calling you." in "Message client" and presses Send. expected: within about 2 s the phone caption shows it; with GlassCam not live and the toggle on, the phone speaks it; a "guide" event is logged.
- JRN-69: steps: send an empty or 200+ character message, or a message to a not-started or ended attempt. expected: rejected with a visible message; no event.
- JRN-70: steps: turn "Speak cues aloud" off, reload, send a cue. expected: the toggle is still off; the caption updates; nothing is spoken.
- JRN-71: steps: connect GlassCam (wss) on the stream, send a cue. expected: the glasses get the guide message; the phone shows the caption but doesn't speak.
- JRN-72: steps: press Repeat cue with GlassCam live, then not live. expected: live → the glasses get the cue again; not live → the phone speaks it again (toggle on); before any cue → "No cue yet".
- JRN-73: steps: press Request help. expected: the page announces "Help requested. Your practitioner has been told."; a "help" event; within about 5 s the client page shows a red "Help requested HH:MM" on that attempt without a manual reload.
- JRN-74: steps: run with no glasses frames for 3 s. expected: the "Use phone camera" button appears.
- JRN-75: steps: press "Use phone camera". expected: the rear camera preview shows; about 1 frame/s counted server-side with heading and steps; nothing stored; Pause stops the camera.
- JRN-76: steps: deny camera or motion permission. expected: "Camera not available" / heading and steps "not available"; the run continues.
- JRN-77: steps: while running, check Wake Lock (where supported). expected: held while running, released on pause/end.
- JRN-78: steps: navigate with VoiceOver / keyboard only. expected: every control has a clear name, order follows the layout, status changes are announced. (human)
- JRN-79: steps: run tests/wss_ingest_check.py and open /device-test. expected: "att-test" still works.
