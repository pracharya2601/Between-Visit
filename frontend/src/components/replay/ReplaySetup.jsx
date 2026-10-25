import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

export default function ReplaySetup({ routeId, isPublic, onStart }) {
  const [info, setInfo] = useState({ status: "loading" });
  const [on, setOn] = useState("v1");
  const [recId, setRecId] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const url = isPublic ? `${API}/demo` : `${API}/routes/${routeId}/recordings`;
    axios.get(url)
      .then((r) => {
        const recs = isPublic ? r.data.recordings : r.data;
        setInfo(recs.length ? { status: "ready", recs } : { status: "none" });
        if (recs.length) setRecId(recs[0].id);
      })
      .catch((e) => setInfo({ status: e.response?.status === 404 ? "none" : "error" }));
  }, [routeId, isPublic]);

  const onClick = async () => {
    setBusy(true);
    setMsg("");
    try {
      await onStart({ on, recording_id: recId || null });
    } catch (e) {
      const d = e.response?.data?.detail;
      setMsg(typeof d === "string" ? d : "Couldn't start the replay. Try again.");
      setBusy(false);
    }
  };

  if (info.status === "loading") return <p role="status" data-testid="replay-setup-loading">Loading the demo…</p>;
  if (info.status === "none") return <p className="bv-strong" role="status" data-testid="replay-no-recording">No demo recording yet.</p>;
  if (info.status === "error") return <p className="bv-error" role="alert" data-testid="replay-setup-error">Couldn't load the demo. Try again.</p>;
  return (
    <section className="bv-panel bv-replay-setup" aria-labelledby="replay-setup-heading" data-testid="replay-setup">
      <h2 id="replay-setup-heading" className="bv-h2">Replay a recorded run</h2>
      <p>Recorded frames go through the same cue engine as a live run. Turn your sound on.</p>
      <fieldset className="bv-fieldset">
        <legend className="bv-label">Route memory</legend>
        <label className="bv-choice">
          <input type="radio" name="replay-on" checked={on === "v1"} onChange={() => setOn("v1")} data-testid="replay-on-v1" />
          <span>On v1 (before corrections)</span>
        </label>
        <label className="bv-choice">
          <input type="radio" name="replay-on" checked={on === "latest"} onChange={() => setOn("latest")} data-testid="replay-on-latest" />
          <span>On latest version</span>
        </label>
      </fieldset>
      {info.recs.length > 1 && (
        <div className="bv-field">
          <label htmlFor="replay-recording" className="bv-label">Recording</label>
          <select id="replay-recording" className="bv-input" value={recId} onChange={(e) => setRecId(e.target.value)} data-testid="replay-recording-select">
            {info.recs.map((r) => <option key={r.id} value={r.id}>{r.label} · {r.frame_count} frames</option>)}
          </select>
        </div>
      )}
      <button type="button" className="bv-btn bv-btn-primary bv-btn-spaced" onClick={onClick} disabled={busy} data-testid="replay-start-button">Start replay</button>
      <p aria-live="polite" role="status" className="bv-cp-msg" data-testid="replay-setup-status">{msg}</p>
    </section>
  );
}
