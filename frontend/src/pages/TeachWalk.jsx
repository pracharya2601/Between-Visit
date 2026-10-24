import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import CopyField from "@/components/CopyField";
import TeachLive from "@/components/teach/TeachLive";

const ENDED = { cancelled: "This walk was cancelled.", expired: "This walk expired after 2 hours without activity." };

export default function TeachWalk() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { status, data } = useApi(`${API}/teach/${id}`);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const act = async (action, then) => {
    setBusy(true);
    try {
      await axios.post(`${API}/teach/${id}/${action}`);
      then();
    } catch (e) {
      setMsg(e.response?.data?.detail || "That didn't work. Try again.");
      setBusy(false);
    }
  };

  if (status !== "ready") {
    return <div role="status" aria-live="polite">{status === "error" ? <p className="bv-error">Teach walk not found</p> : <p>Loading…</p>}</div>;
  }
  const s = data;
  return (
    <div className="bv-stack">
      <section aria-labelledby="teach-walk-heading">
        <p className="bv-eyebrow">Teach by walking · {s.route_name}</p>
        <h1 id="teach-walk-heading" className="bv-h1">Teach walk</h1>
      </section>
      {s.status === "active" ? (
        <>
          <p className="bv-warning" data-testid="teach-instruction">Start at the route's entrance and face the way you'll walk.</p>
          <section className="bv-panel" aria-labelledby="teach-connect-heading">
            <h2 id="teach-connect-heading" className="bv-h2">GlassCam connection</h2>
            <CopyField id="teach-server-url" label="Server URL" value={API} />
            <CopyField id="teach-stream-id" label="Stream ID" value={s.stream_id} />
            <CopyField id="teach-key" label="Key" value={s.key || ""} />
          </section>
          <TeachLive sessionId={id} />
          <button type="button" className="bv-btn bv-run-btn bv-run-start" disabled={busy} onClick={() => act("finish", () => navigate(`/teach/${id}/review`))} data-testid="teach-finish-button">Finish walk</button>
          {confirmCancel ? (
            <div role="alertdialog" aria-labelledby="cancel-q" className="bv-panel">
              <p id="cancel-q" className="bv-strong">Discard this walk? The map and proposed checkpoints will be deleted.</p>
              <button type="button" className="bv-btn bv-run-btn bv-run-end" disabled={busy} onClick={() => act("cancel", () => navigate("/routes"))} data-testid="teach-cancel-confirm-button">Yes, cancel the walk</button>
              <button type="button" className="bv-btn bv-run-btn" onClick={() => setConfirmCancel(false)} data-testid="teach-cancel-keep-button">Keep walking</button>
            </div>
          ) : (
            <button type="button" className="bv-btn bv-run-btn bv-run-end" onClick={() => setConfirmCancel(true)} data-testid="teach-cancel-button">Cancel walk</button>
          )}
        </>
      ) : s.status === "finished" && !s.saved ? (
        <p><Link to={`/teach/${id}/review`} className="bv-link" data-testid="teach-review-link">Review this walk</Link></p>
      ) : (
        <p className="bv-error" data-testid="teach-ended">{ENDED[s.status] || "This walk has been saved."}</p>
      )}
      <p role="status" aria-live="polite" className="bv-error-text" data-testid="teach-walk-msg">{msg}</p>
    </div>
  );
}
