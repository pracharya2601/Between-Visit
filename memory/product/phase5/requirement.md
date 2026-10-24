# Phase 5 Requirements: Client Run Page
Version: phase-5

Goal: a blind or low-vision client runs an exercise from /run/{id}#key=… on a phone. They start, pause, resume and end, hear and read cues, ask for help, and fall back to the phone camera when the glasses aren't streaming. The practitioner sees help requests and can message the client. See ../overview.md. Phases 1–4 must keep working.

## Cleanup
- REQ-129 [event] When this phase deploys, the system shall delete "Reception route (synthetic)" and "Unsaved draft (synthetic)" with their checkpoints, route_versions, exercises, attempts and attempt_events; their photos become unservable (404). Idempotent.
- REQ-130 [always] Data created for checks shall be deleted after the checks; anything that can't be deleted shall be reported.

## Status & events
- REQ-131 [always] Attempt status shall be one of not_started, running, paused, ended.
- REQ-132 [event] When Start is pressed on a not_started attempt, the system shall set status running, set started_at, and log a "start" event.
- REQ-133 [event] When Pause is pressed while running, the system shall set status paused and log a "pause" event.
- REQ-134 [event] When Resume is pressed while paused, the system shall set status running and log a "resume" event.
- REQ-135 [event] When End is pressed while running or paused, the system shall set status ended, set ended_at, and log an "end" event.
- REQ-136 [unwanted] If a transition isn't allowed (e.g. Start on an ended attempt), then the system shall return 409 and change nothing.
- REQ-137 [always] Every run-page API call shall require the attempt key in the X-Stream-Key header (never in the URL); a wrong or missing key returns 401.
- REQ-138 [always] attempt_events shall have attempt_id, t (UTC), type, text, spoken, suppressed_reason, checkpoint, uncertain, using the fields that apply.

## Layout (one column, phone, VoiceOver-friendly)
- REQ-139 [always] The page shall show very large high-contrast buttons, at least 64px tall and full width (interpreted): Start, Pause/Resume (one toggling button), Repeat cue, Request help, End.
- REQ-140 [state] While not_started, only Start, Request help and the summary shall be enabled. (interpreted)
- REQ-141 [state] While running or paused, Start shall be hidden or disabled; Pause/Resume, Repeat cue, Request help and End shall be enabled.
- REQ-142 [state] While ended, the page shall show "This run has ended" and disable all controls.
- REQ-143 [event] When End is pressed, the system shall ask "End this run?" with confirm/cancel before ending. (interpreted)
- REQ-144 [always] The summary shall show the goal, the checkpoint names in order from the pinned route version, and the stop-and-contact rule.
- REQ-145 [always] The page shall show the stream ID and key for GlassCam, each with a copy button.
- REQ-146 [always] The page shall show elapsed time (running time, paused time excluded, interpreted), heading in degrees, and "about N steps".
- REQ-147 [always] The page shall have a large caption area with aria-live="assertive" showing the newest cue.
- REQ-148 [always] Every control shall have an accessible name; status changes shall be announced; the reading order follows the visual order.

## Start & permissions
- REQ-149 [event] When Start is tapped, the system shall request the iOS DeviceMotion/DeviceOrientation permission inside that same tap handler.
- REQ-150 [event] When Start is tapped, the system shall unlock speechSynthesis inside that tap (iOS needs a gesture).
- REQ-151 [unwanted] If motion permission is denied or unavailable, then the run shall still start and heading/steps shall show "not available".
- REQ-152 [state] While running, the system shall hold a screen Wake Lock if available, re-acquiring it when the page becomes visible again.
- REQ-153 [event] When paused or ended, the system shall release the Wake Lock.

## Heading & steps
- REQ-154 [always] Heading shall come from webkitCompassHeading on iOS, or from DeviceOrientation alpha elsewhere (approximate).
- REQ-155 [always] Steps shall be a rough count from DeviceMotion acceleration peaks, shown as "about N steps", counting only while running.

## Cues
- REQ-156 [state] While the attempt isn't ended, the run page shall poll for new guide cues every 1 s.
- REQ-157 [event] When a new cue arrives, the system shall show it as the caption.
- REQ-158 [event] When a new cue arrives while GlassCam isn't live on this stream and "Speak cues aloud" is on, the phone shall speak it with speechSynthesis.
- REQ-159 [state] While GlassCam is live, the phone shall not speak cues (the glasses speak them).
- REQ-160 [always] The page shall have a "Speak cues aloud" toggle, on by default, remembered on the phone (localStorage).
- REQ-161 [event] When Repeat cue is pressed, the system shall re-announce the last cue in the caption.
- REQ-162 [event] When Repeat cue is pressed while GlassCam isn't live and speak is on, the phone shall speak the last cue again.
- REQ-163 [event] When Repeat cue is pressed while GlassCam is live, the system shall resend the last cue to GlassCam.
- REQ-164 [unwanted] If there's no cue yet, then Repeat cue shall announce "No cue yet".
- REQ-165 [always] Each guide cue shall be logged as a "guide" attempt_event with spoken true or false.

## Help
- REQ-166 [event] When Request help is pressed, the system shall log a "help" event and announce "Help requested. Your practitioner has been told."
- REQ-167 [unwanted] If the help request fails, then the page shall announce "Help didn't send. Call your practitioner." and allow a retry.
- REQ-168 [always] The practitioner's client page shall show a red "Help requested HH:MM" (local time of the latest help event) on that attempt.
- REQ-169 [always] The client page shall refresh its data every 5 s.

## Message client
- REQ-170 [state] While an attempt is running or paused (interpreted), the client page shall show a "Message client" box with a Send button on that attempt.
- REQ-171 [event] When Send is pressed, the system shall create a guide cue for that attempt, delivered to the phone via polling and to GlassCam via WebSocket if live.
- REQ-172 [unwanted] If the message is empty or 200+ characters, then the system shall reject it with a visible message.
- REQ-173 [unwanted] If the attempt is ended or not started, then the system shall reject the message (409).

## Phone camera fallback
- REQ-174 [state] While running and no glasses frames have arrived for 3 s, the page shall show a "Use phone camera" button.
- REQ-175 [event] When "Use phone camera" is pressed, the system shall open the rear camera (facingMode environment) and show a small preview.
- REQ-176 [state] While the phone camera is on and running, the system shall post one JPEG per second to POST /api/attempts/{id}/frame with X-Stream-Key, ?heading=&steps=.
- REQ-177 [event] When paused, ended or "Stop phone camera" is pressed, the system shall stop the camera and the posting.
- REQ-178 [unwanted] If camera permission is denied, then the page shall announce "Camera not available" and the run shall continue.
- REQ-179 [always] Frames shall never be stored (client or server); the server counts and discards them as in Phase 2.

## Quality requirements
```
Q-21 Tag: Accessibility.VoiceOver
     Scale: controls a VoiceOver user can find, name and activate unaided
     Meter: human (iPhone VoiceOver)
     Must: 100%   Plan: 100%
Q-22 Tag: Cue.Latency
     Scale: seconds from "Message client" send to caption shown on the phone
     Meter: 5 trials
     Must: 3   Plan: 1.5
Q-23 Tag: Help.Latency
     Scale: seconds from Request help to red alert on the client page
     Meter: 3 trials
     Must: 10   Plan: 6
Q-24 Tag: Cue.DoubleSpeech
     Scale: cues spoken by both glasses and phone
     Meter: human
     Must: 0   Plan: 0
Q-25 Tag: Privacy.Frames
     Scale: frame bytes stored anywhere
     Meter: DB + disk inspection after 10 phone frames
     Must: 0   Plan: 0
Q-26 Tag: Mobile.Usability
     Scale: horizontal scroll at 390px; buttons under 64px tall
     Meter: screenshot
     Must: 0   Plan: 0
```
