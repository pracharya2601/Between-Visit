import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";
import PhotoPicker from "@/components/PhotoPicker";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const errText = (e, fallback) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : fallback);

function useDebouncedPatch(cp, onChange) {
  const [name, setName] = useState(cp.name);
  const [text, setText] = useState(cp.landmark_text);
  const timer = useRef(null);
  useEffect(() => { setText(cp.landmark_text); }, [cp.landmark_text]);

  const flush = async (fields = { name, landmark_text: text }) => {
    clearTimeout(timer.current);
    if (fields.name === cp.name && fields.landmark_text === cp.landmark_text) return cp;
    const r = await axios.patch(`${API}/checkpoints/${cp.id}`, fields);
    onChange(r.data);
    return r.data;
  };
  const edit = (field, value) => {
    const fields = { name, landmark_text: text, [field]: value };
    field === "name" ? setName(value) : setText(value);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => flush(fields).catch(() => {}), 500);
  };
  return { name, text, edit, flush, dirty: name !== cp.name || text !== cp.landmark_text };
}

export default function CheckpointCard({ cp, index, total, onChange, onMove, onRemove }) {
  const { name, text, edit, flush, dirty } = useDebouncedPatch(cp, onChange);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const n = index + 1;
  const p = `checkpoint-${n}`;
  const canApprove = name.trim() && cp.photo_url && text.trim();
  const approved = cp.approved && !dirty;

  const run = async (label, fn) => {
    setBusy(true);
    setMsg(label);
    try { await fn(); } finally { setBusy(false); }
  };

  const onFile = (file) => run("Checking the photo and asking AI for a landmark…", async () => {
    const form = new FormData();
    form.append("file", file);
    try {
      await flush();
      const r = await axios.post(`${API}/checkpoints/${cp.id}/photo`, form);
      onChange(r.data.checkpoint);
      setMsg(r.data.message);
    } catch (e) {
      setMsg(errText(e, "Couldn't add the photo. Try again."));
    }
  });

  const onApprove = () => run("Approving…", async () => {
    try {
      await flush();
      const r = await axios.post(`${API}/checkpoints/${cp.id}/approve`);
      onChange(r.data);
      setMsg(`Checkpoint ${n} approved`);
    } catch (e) {
      setMsg(errText(e, "Couldn't approve. Try again."));
    }
  });

  return (
    <li className={`bv-cp ${approved ? "bv-cp-approved" : ""}`} data-testid={p}>
      <fieldset className="bv-cp-fieldset">
        <legend className="bv-cp-legend">
          <span data-testid={`${p}-number`}>Checkpoint {n}</span>
          <span className={`bv-tag ${approved ? "bv-tag-ok" : ""}`} data-testid={`${p}-approval-state`}>{approved ? "Approved" : "Not approved"}</span>
          {cp.photo_pending && <span className="bv-tag" data-testid={`${p}-photo-pending`}>Finding a photo…</span>}
          {cp.needs_photo && <span className="bv-tag bv-tag-warn" data-testid={`${p}-needs-photo`}>Needs photo</span>}
          {cp.ai_unavailable && cp.photo_url && !cp.landmark_text && <span className="bv-tag" data-testid={`${p}-ai-unavailable`}>AI suggestion unavailable</span>}
        </legend>
        <div className="bv-field">
          <label htmlFor={`${p}-name`} className="bv-label">Checkpoint name</label>
          <input id={`${p}-name`} className="bv-input" value={name} onChange={(e) => edit("name", e.target.value)} onBlur={() => flush().catch(() => {})} data-testid={`${p}-name-input`} />
        </div>
        <div className="bv-field">
          <p className="bv-label" id={`${p}-photo-label`}>Photo of the empty space</p>
          {cp.photo_url ? (
            <img src={`${BACKEND}${cp.photo_url}`} alt={`Photo for checkpoint ${n}${name ? `, ${name}` : ""}`} className="bv-photo" data-testid={`${p}-photo`} />
          ) : (
            <p className="bv-hint" data-testid={`${p}-no-photo`}>No photo yet. Make sure no one is in the frame.</p>
          )}
          <PhotoPicker idPrefix={p} busy={busy} onFile={onFile} onReject={setMsg} />
        </div>
        <div className="bv-field">
          <label htmlFor={`${p}-text`} className="bv-label">
            Landmark text {cp.ai_suggested && !dirty && <span className="bv-tag bv-tag-ai" data-testid={`${p}-ai-label`}>Suggested by AI</span>}
          </label>
          <textarea id={`${p}-text`} rows={3} className="bv-input" value={text} onChange={(e) => edit("landmark_text", e.target.value)} onBlur={() => flush().catch(() => {})} data-testid={`${p}-text-input`} />
        </div>
        <p aria-live="polite" role="status" className="bv-cp-msg" data-testid={`${p}-status`}>{msg}</p>
        <div className="bv-btn-row">
          <button type="button" className="bv-btn bv-btn-approve" disabled={busy || !canApprove || approved} onClick={onApprove} data-testid={`${p}-approve-button`}>
            {approved ? "Approved" : "Approve"}
          </button>
          <button type="button" className="bv-btn" disabled={busy || index === 0} onClick={() => onMove(cp.id, "up")} aria-label={`Move checkpoint ${n} up`} data-testid={`${p}-move-up-button`}>Move up</button>
          <button type="button" className="bv-btn" disabled={busy || index === total - 1} onClick={() => onMove(cp.id, "down")} aria-label={`Move checkpoint ${n} down`} data-testid={`${p}-move-down-button`}>Move down</button>
          <button type="button" className="bv-btn bv-btn-danger" disabled={busy} onClick={() => onRemove(cp.id)} aria-label={`Remove checkpoint ${n}`} data-testid={`${p}-remove-button`}>Remove</button>
        </div>
      </fieldset>
    </li>
  );
}
