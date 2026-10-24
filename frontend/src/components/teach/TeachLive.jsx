import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

export default function TeachLive({ sessionId }) {
  const [s, setS] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const tick = () => axios.get(`${API}/teach/${sessionId}/status`)
      .then((r) => alive && (setS(r.data), setFailed(false)))
      .catch(() => alive && setFailed(true));
    tick();
    const t = setInterval(tick, 1000);
    return () => { alive = false; clearInterval(t); };
  }, [sessionId]);

  return (
    <section className="bv-panel" aria-labelledby="teach-live-heading" data-testid="teach-live">
      <h2 id="teach-live-heading" className="bv-h2">Live</h2>
      <p role="status" aria-live="polite" className={`bv-badge ${s?.live ? "bv-badge-live" : ""}`} data-testid="teach-live-status">
        {failed ? "Couldn't load status" : s?.live ? "Live" : "Not connected"}
      </p>
      <dl className="bv-dl">
        <dt>Metres walked</dt><dd data-testid="teach-metres">{(s?.metres_walked ?? 0).toFixed(1)} m</dd>
        <dt>3D points</dt><dd data-testid="teach-points">{(s?.points ?? 0).toLocaleString()}{s?.point_limit_reached && " (Point limit reached)"}</dd>
        <dt>Checkpoints proposed</dt><dd data-testid="teach-proposed">{s?.checkpoints_proposed ?? 0}</dd>
      </dl>
    </section>
  );
}
