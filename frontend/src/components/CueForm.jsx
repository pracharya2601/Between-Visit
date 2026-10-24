import { useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

export default function CueForm({ attemptId }) {
  const [text, setText] = useState("");
  const [priority, setPriority] = useState("1");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setResult("");
    try {
      await axios.post(`${API}/attempts/${attemptId}/cue`, { text, priority: Number(priority) });
      setResult("Sent");
    } catch (err) {
      const d = err.response?.data?.detail;
      setResult(typeof d === "string" ? d : Array.isArray(d) ? "Cue must be 1 to 199 characters" : "Couldn't send cue");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="bv-panel" aria-labelledby="cue-heading" data-testid="cue-form">
      <h2 id="cue-heading" className="bv-h2">Send a test cue</h2>
      <div className="bv-field">
        <label htmlFor="cue-text" className="bv-label">Cue text (1 to 199 characters)</label>
        <input id="cue-text" className="bv-input" value={text} onChange={(e) => setText(e.target.value)} data-testid="cue-text-input" />
      </div>
      <div className="bv-field">
        <label htmlFor="cue-priority" className="bv-label">Priority</label>
        <select id="cue-priority" className="bv-input bv-select" value={priority} onChange={(e) => setPriority(e.target.value)} data-testid="cue-priority-select">
          <option value="0">0</option>
          <option value="1">1</option>
          <option value="2">2</option>
        </select>
      </div>
      <button type="submit" className="bv-btn bv-btn-primary" disabled={busy} data-testid="send-cue-button">Send test cue</button>
      <p aria-live="assertive" role="status" className={result === "Sent" ? "bv-ok" : "bv-error-text"} data-testid="cue-result">{result}</p>
    </form>
  );
}
