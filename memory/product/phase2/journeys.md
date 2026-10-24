# Phase 2 Journeys
(Phase 1 journeys JRN-1..12 stay valid, except as superseded below.)

- JRN-13: steps: inspect the exercises and attempts models. expected: exercises has no stream_id or key; attempts has stream_id and a hashed key. superseded: [] (JRN-11's "no exercise key returned" is still true; it's now trivially true).
- JRN-14: steps: restart the backend twice. expected: exactly one attempt with stream_id "att-test" for Client A; the key shown on /device-test is unchanged.
- JRN-15: steps: connect via wss://<public preview>/api/ws/ingest/att-test?key=<correct>. expected: connects; first message is {"viewers": 0}.
- JRN-16: steps: connect with a wrong key, with no key, and to stream "nope". expected: each closes with code 1008.
- JRN-17: steps: send 5 small JPEG frames. expected: /device-test shows frames received 5, seconds since last frame resets, status "Live".
- JRN-18: steps: send a motion text message, then a frame. expected: /device-test shows that motion (src "glasses") as the last motion.
- JRN-19: steps: send a 1.5 MB binary message, then a small frame. expected: frames dropped goes up by 1, the connection stays open, and frames received goes up by 1.
- JRN-20: steps: on /device-test type "Turn left at the bench" and press "Send test cue". expected: the device gets {"type":"guide","text":"Turn left at the bench","priority":<0-2>,"speak":true}; the page shows "Sent".
- JRN-21: steps: send a cue of 200+ characters, or an empty one. expected: rejected with a clear error; the device gets nothing.
- JRN-22: steps: send a cue with no device connected. expected: an error that says "Not connected".
- JRN-23: steps: disconnect, then reconnect on the same stream. expected: accepted; counters keep their values; status goes Not connected → Live.
- JRN-24: steps: connect device A, then device B on the same stream. expected: A's socket closes; B gets cues; status "Live".
- JRN-25: steps: POST /api/attempts/<test id>/frame?heading=90&steps=12 with X-Stream-Key and a JPEG body. expected: 2xx; frames received +1; last motion shows heading 90 and steps 12.
- JRN-26: steps: POST the frame with a wrong or missing key, an unknown id, and a 1.5 MB body. expected: 401/403, 404 and 413 in turn; frames received unchanged.
- JRN-27: steps: grep the backend logs after the steps above. expected: no "?key=", no key value, no frame bytes; no frames on disk or in the DB.
- JRN-28: steps: open /device-test. expected: shows Server URL = public URL + "/api", stream ID "att-test" and the key, each copy button copies its value; the footer is present; all controls can be reached by keyboard.
- JRN-29: steps: GET the list endpoints (practices, practitioners, clients, and any attempts list if there is one). expected: no key or key hash in any response.
