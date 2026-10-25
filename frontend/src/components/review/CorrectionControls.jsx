import { useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

const statusText = (c) => (c.action === "dismiss" ? "Dismissed" : `Saved to route memory as v${c.new_route_version}`);

function EditForm({ p, item, onSubmit, onCancel, busy }) {
  const [label, setLabel] = useState(item.entity.label);
  const [side, setSide] = useState(item.entity.side);
  const bad = !label.trim() || label.trim().length > 40;
  return (
    <form className="bv-correct-form" onSubmit={(e) => { e.preventDefault(); if (!bad) onSubmit({ action: "edit", label: label.trim(), side }); }} data-testid={`${p}-edit-form`}>
      <label className="bv-label" htmlFor={`${p}-label`}>Object name</label>
      <input id={`${p}-label`} className="bv-input" value={label} maxLength={40} onChange={(e) => setLabel(e.target.value)} aria-invalid={bad} data-testid={`${p}-edit-label`} />
      <label className="bv-label" htmlFor={`${p}-side`}>Side</label>
      <select id={`${p}-side`} className="bv-input" value={side} onChange={(e) => setSide(e.target.value)} data-testid={`${p}-edit-side`}>
        <option value="ahead">Ahead</option><option value="left">Left</option><option value="right">Right</option>
      </select>
      <div className="bv-btn-row">
        <button type="submit" className="bv-btn bv-btn-primary" disabled={bad || busy} data-testid={`${p}-edit-save`}>Confirm edited object</button>
        <button type="button" className="bv-btn" onClick={onCancel} data-testid={`${p}-edit-cancel`}>Cancel</button>
      </div>
    </form>
  );
}

export default function CorrectionControls({ item, onChanged }) {
  const p = `timeline-item-${item.id}`;
  const [done, setDone] = useState(item.correction);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const send = (body) => {
    setBusy(true); setError("");
    axios.post(`${API}/attempt-events/${item.id}/correction`, body)
      .then((r) => { setDone(r.data); onChanged?.(); })
      .catch((e) => {
        const c = e.response?.data?.detail?.correction;
        if (c) setDone(c); else setError(e.response?.status === 422 ? "Check the object name (1 to 40 characters)." : "Couldn't save the correction. Try again.");
      })
      .finally(() => setBusy(false));
  };

  return (
    <div className="bv-correct" data-testid={`${p}-correction`}>
      <p role="status" aria-live="polite" className="bv-strong" data-testid={`${p}-correction-status`}>{done ? statusText(done) : ""}</p>
      {!done && !editing && (
        <div className="bv-btn-row" role="group" aria-label={`Correct ${item.entity.label}`}>
          <button type="button" className="bv-btn bv-btn-primary" disabled={busy} onClick={() => send({ action: "confirm" })} data-testid={`${p}-confirm-button`}>Confirm</button>
          <button type="button" className="bv-btn" disabled={busy} onClick={() => setEditing(true)} data-testid={`${p}-edit-button`}>Edit</button>
          <button type="button" className="bv-btn" disabled={busy} onClick={() => send({ action: "dismiss" })} data-testid={`${p}-dismiss-button`}>Dismiss</button>
        </div>
      )}
      {!done && editing && <EditForm p={p} item={item} busy={busy} onSubmit={send} onCancel={() => setEditing(false)} />}
      {error && <p role="alert" className="bv-error" data-testid={`${p}-correction-error`}>{error}</p>}
    </div>
  );
}
