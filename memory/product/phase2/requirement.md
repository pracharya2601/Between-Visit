# Phase 2 Requirements: Device Ingest (no vision)
Version: phase-2

Goal: a device (glasses app or phone) can stream JPEG frames and motion data for one attempt. The server counts the frames and throws them away, and can push spoken guide cues back. A practitioner test page shows it live. See ../overview.md.

## Data model change
- REQ-20 [always] The system shall remove stream_id and key from the exercises model.
- REQ-21 [always] The system shall add stream_id (unique) and key to the attempts model, one pair per attempt.
- REQ-22 [always] The system shall store only a hash of an attempt key, never the plain key. (interpreted)
- REQ-23 [event] When the backend starts and no attempt has stream_id "att-test", the system shall seed a test attempt for Client A with stream_id "att-test" and a random key.
- REQ-24 [always] The system shall seed one minimal synthetic route "Test route (synthetic)" and one exercise for Client A so the test attempt has an exercise_id. (interpreted)
- REQ-25 [unwanted] If the test attempt already exists at startup, then the system shall insert no new attempt and shall keep its key.
- REQ-26 [always] The system shall keep the test attempt's plain key retrievable only for /device-test (e.g. a dedicated test-config document or env), never in any list endpoint. (interpreted)

## WebSocket /api/ws/ingest/{stream_id}?key=<key>
- REQ-27 [unwanted] If the stream_id is unknown, then the system shall close the socket with code 1008.
- REQ-28 [unwanted] If the key is wrong or missing, then the system shall close the socket with code 1008.
- REQ-29 [event] When a device connects with a valid key, the system shall send {"viewers": 0} exactly once (always 0 for now).
- REQ-30 [event] When a binary message of 1 MB or less arrives, the system shall increment frames_received, record the last frame time and size, and discard the bytes.
- REQ-31 [unwanted] If a binary message is over 1 MB, then the system shall drop it, increment frames_dropped, and keep the connection open.
- REQ-32 [event] When a text message {"type":"motion","ts_ns","q","acc","gyro","mag","src"} arrives, the system shall hold it and pair it with the next accepted frame as that frame's last motion.
- REQ-33 [unwanted] If a second motion message arrives before a frame, then the system shall replace the held motion with the newer one. (interpreted)
- REQ-34 [unwanted] If a text message is invalid JSON or an unknown type, then the system shall ignore it and keep the connection open. (interpreted)
- REQ-35 [event] When a practitioner sends a test cue, the system shall push {"type":"guide","text":...,"priority":0|1|2,"speak":true} to the live device socket for that stream.
- REQ-36 [unwanted] If guide text is empty or 200 characters or longer, then the system shall reject it with a 422 error and not send it.
- REQ-37 [unwanted] If no device is connected when a cue is sent, then the system shall return an error ("Not connected") and send nothing.
- REQ-38 [event] When a device reconnects on the same stream, the system shall accept it and keep the counters.
- REQ-39 [event] When a new device connects while another is live on the same stream, the system shall close the old socket and make the new one live.
- REQ-40 [always] The system shall never write the ingest URL or key to any log. Access logging is off for this route.
- REQ-41 [always] The system shall never write frame bytes to disk, the database or logs.

## Phone fallback
- REQ-42 [event] When POST /api/attempts/{id}/frame is called with a correct X-Stream-Key header and a JPEG body of 1 MB or less, the system shall count it like a WebSocket frame, store the optional heading and steps query params as last motion/sensor info, and discard the bytes.
- REQ-43 [unwanted] If the X-Stream-Key header is wrong or missing, then the system shall return 401 or 403 and count nothing.
- REQ-44 [unwanted] If the attempt id is unknown, then the system shall return 404.
- REQ-45 [unwanted] If the body is over 1 MB, then the system shall return 413 and increment frames_dropped.

## /device-test page (practitioner side, no login)
- REQ-46 [always] The page shall show the Server URL as the public backend URL + "/api", with a copy button.
- REQ-47 [always] The page shall show stream ID "att-test" with a copy button.
- REQ-48 [always] The page shall show the test attempt's key with a copy button.
- REQ-49 [state] While a device socket is live, the page shall show status "Live"; otherwise "Not connected".
- REQ-50 [always] The page shall show frames received, frames dropped, seconds since the last frame, and the last motion, refreshing at least once per second.
- REQ-51 [event] When the practitioner types text and presses "Send test cue", the system shall send a guide message and show the result ("Sent" or the error).
- REQ-52 [always] The page shall meet the Phase 1 accessibility rules (labelled controls, keyboard operable, aria-live for status changes) and show the footer.

## Infrastructure
- REQ-53 [always] The ingest WebSocket shall work from outside through the public preview URL over wss://. If it doesn't, the builder shall report that and build no workaround.

## Quality requirements
```
Q-6  Tag: Privacy.Frames
     Scale: frame bytes persisted anywhere (disk, DB, logs)
     Meter: grep logs + DB inspection after sending 20 frames
     Must: 0   Plan: 0
Q-7  Tag: Privacy.KeyInLogs
     Scale: log lines containing the key or "?key="
     Meter: grep backend logs after 5 connects
     Must: 0   Plan: 0
Q-8  Tag: Ingest.Latency
     Scale: seconds from frame sent to counter change on /device-test
     Meter: manual, 5 trials
     Must: 3   Plan: 1.5
Q-9  Tag: Ingest.Cue
     Scale: seconds from "Send test cue" to device receiving guide msg
     Meter: wss client, 5 trials
     Must: 2   Plan: 0.5
Q-10 Tag: Ingest.Reachability
     Scale: wss connect success through public preview URL
     Meter: external wss client, 3 trials
     Must: 3/3   Plan: 3/3
```
