import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { runPath } from "@/components/OneTimeConfirmation";

const STATUS = { not_started: "Not started", running: "Running", paused: "Paused", ended: "Ended", pending: "Test" };
const hhmm = (t) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

function MessageForm({ attemptId, p }) {
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return setMsg("Type a message first.");
    if (t.length > 199) return setMsg("Messages must be under 200 characters.");
    setBusy(true);
    try {
      const r = await axios.post(`${API}/attempts/${attemptId}/message`, { text: t });
      setText("");
      setMsg(r.data.sent_to_glasses ? "Sent to the phone and the glasses" : "Sent to the phone");
    } catch (ex) {
      const d = ex.response?.data?.detail;
      setMsg(typeof d === "string" ? d : "Couldn't send the message. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="bv-message" data-testid={`${p}-message-form`}>
      <label htmlFor={`${p}-message`} className="bv-label">Message client</label>
      <textarea id={`${p}-message`} rows={2} className="bv-input" value={text} onChange={(e) => setText(e.target.value)} data-testid={`${p}-message-input`} />
      <button type="submit" className="bv-btn bv-btn-spaced" disabled={busy} data-testid={`${p}-message-send-button`}>Send</button>
      <p aria-live="polite" role="status" className="bv-cp-msg" data-testid={`${p}-message-status`}>{msg}</p>
    </form>
  );
}

export default function AttemptRow({ a }) {
  const p = `attempt-${a.stream_id}`;
  return (
    <li data-testid={p}>
      <span className="bv-mono">{a.stream_id}</span> · <span data-testid={`${p}-status`}>{STATUS[a.status] ?? a.status}</span>
      {a.last_help_at && (
        <p className="bv-help-alert" role="alert" data-testid={`${p}-help-alert`}>Help requested {hhmm(a.last_help_at)}</p>
      )}
      <br />
      <Link to={runPath(a.id)} className="bv-link bv-mono" data-testid={`${p}-run-link`}>{runPath(a.id)}</Link>
      {(a.status === "running" || a.status === "paused") && <MessageForm attemptId={a.id} p={p} />}
    </li>
  );
}
