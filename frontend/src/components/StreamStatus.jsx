import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

function formatMotion(m) {
  if (!m) return "None yet";
  return Object.entries(m)
    .filter(([k, v]) => k !== "type" && v !== null && v !== undefined)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
    .join("; ");
}

export default function StreamStatus({ attemptId }) {
  const [s, setS] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const tick = () =>
      axios.get(`${API}/attempts/${attemptId}/status`)
        .then((r) => alive && (setS(r.data), setFailed(false)))
        .catch(() => alive && setFailed(true));
    tick();
    const t = setInterval(tick, 1000);
    return () => { alive = false; clearInterval(t); };
  }, [attemptId]);

  const live = s?.live;
  return (
    <section className="bv-panel" aria-labelledby="status-heading" data-testid="stream-status">
      <h2 id="status-heading" className="bv-h2">Device status</h2>
      <p aria-live="polite" role="status" className={`bv-badge ${live ? "bv-badge-live" : ""}`} data-testid="device-status">
        {failed ? "Couldn't load status" : live ? "Live" : "Not connected"}
      </p>
      <dl className="bv-dl">
        <dt>Frames received</dt><dd data-testid="frames-received">{s?.frames_received ?? 0}</dd>
        <dt>Frames dropped</dt><dd data-testid="frames-dropped">{s?.frames_dropped ?? 0}</dd>
        <dt>Seconds since last frame</dt><dd data-testid="seconds-since-last-frame">{s?.seconds_since_last_frame ?? "No frames yet"}</dd>
        <dt>Last motion</dt><dd className="bv-mono" data-testid="last-motion">{formatMotion(s?.last_motion)}</dd>
      </dl>
    </section>
  );
}
