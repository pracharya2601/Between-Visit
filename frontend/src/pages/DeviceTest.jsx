import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";
import CopyField from "@/components/CopyField";
import StreamStatus from "@/components/StreamStatus";
import CueForm from "@/components/CueForm";

export default function DeviceTest() {
  const [cfg, setCfg] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    axios.get(`${API}/device-test/config`).then((r) => setCfg(r.data)).catch(() => setError(true));
  }, []);

  return (
    <div className="bv-stack">
      <section aria-labelledby="device-test-heading">
        <p className="bv-eyebrow">Practitioner tool</p>
        <h1 id="device-test-heading" className="bv-h1">Device test</h1>
        <p className="bv-lead">Connect the glasses app or a phone to the synthetic test attempt and watch frames arrive. Frames are counted and then discarded.</p>
      </section>
      <div aria-live="polite" role="status" data-testid="device-test-load-status">
        {!cfg && !error && <p>Loading test attempt…</p>}
        {error && <p className="bv-error">Couldn't load the test attempt</p>}
      </div>
      {cfg && (
        <>
          <section className="bv-panel" aria-labelledby="connect-heading">
            <h2 id="connect-heading" className="bv-h2">Connection details</h2>
            <CopyField id="server-url" label="Server URL" value={API} />
            <CopyField id="stream-id" label="Stream ID" value={cfg.stream_id} />
            <CopyField id="stream-key" label="Key" value={cfg.key} />
          </section>
          <StreamStatus attemptId={cfg.attempt_id} />
          <CueForm attemptId={cfg.attempt_id} />
        </>
      )}
    </div>
  );
}
