import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

const LABEL = "Draft written by AI from the attempt log. Review before saving.";
const when = (iso) => new Date(iso).toLocaleString([], { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });

function SavedNote({ note }) {
  return (
    <div data-testid="progress-note-saved">
      <p className="bv-strong" data-testid="progress-note-meta">Approved by {note.author}, {when(note.approved_at)}</p>
      <p className="bv-note-text" data-testid="progress-note-text">{note.text}</p>
      <details className="bv-details" data-testid="progress-note-original">
        <summary>Original AI draft</summary>
        <p className="bv-note-text">{note.ai_draft}</p>
      </details>
    </div>
  );
}

function DraftEditor({ draft, attemptId, onSaved }) {
  const [text, setText] = useState(draft.draft);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const save = () => {
    if (!text.trim()) { setMsg("The note is empty. Write or restore the note before saving."); return; }
    setBusy(true); setMsg("");
    axios.post(`${API}/attempts/${attemptId}/note`, { draft_id: draft.draft_id, text })
      .then((r) => onSaved(r.data))
      .catch((e) => setMsg(typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Couldn't save the note. Try again."))
      .finally(() => setBusy(false));
  };
  return (
    <div className="bv-stack-sm">
      {!draft.numbers_ok && <p className="bv-hint" data-testid="progress-note-check-numbers">Check numbers: some numbers in the draft aren't in the attempt log ({draft.unknown_numbers.join(", ")}).</p>}
      <label htmlFor="progress-note-text" className="bv-label">{LABEL}</label>
      <textarea id="progress-note-text" className="bv-input bv-note-area" value={text} onChange={(e) => setText(e.target.value)} rows={18} data-testid="progress-note-textarea" />
      <button type="button" className="bv-btn bv-btn-primary" onClick={save} disabled={busy} data-testid="progress-note-save-button">Approve and save</button>
      <p role="alert" className="bv-error" data-testid="progress-note-save-error">{msg}</p>
    </div>
  );
}

export default function ProgressNote({ attemptId, status }) {
  const [note, setNote] = useState(undefined);
  const [draft, setDraft] = useState(null);
  const [state, setState] = useState("");
  useEffect(() => { axios.get(`${API}/attempts/${attemptId}/note`).then((r) => setNote(r.data.note)).catch(() => setNote(null)); }, [attemptId]);
  const ended = status === "ended";
  const start = () => {
    setState("drafting"); setDraft(null);
    axios.post(`${API}/attempts/${attemptId}/note/draft`, null, { timeout: 60000 })
      .then((r) => { setDraft(r.data); setState(""); })
      .catch(() => setState("Couldn't draft a note. Try again."));
  };
  return (
    <section className="bv-panel" aria-labelledby="progress-note-heading" data-testid="progress-note">
      <h2 id="progress-note-heading" className="bv-h2">Progress note</h2>
      {note ? <SavedNote note={note} /> : note === null && (
        <>
          {!draft && (
            <button type="button" className="bv-btn bv-btn-primary" onClick={start} disabled={!ended || state === "drafting"} aria-describedby={ended ? undefined : "progress-note-unavailable"} data-testid="progress-note-draft-button">Draft progress note</button>
          )}
          {!ended && <p id="progress-note-unavailable" className="bv-hint" data-testid="progress-note-unavailable">Available after the run ends</p>}
          <p role="status" aria-live="polite" className={state.startsWith("Couldn't") ? "bv-error" : ""} data-testid="progress-note-status">{state === "drafting" ? "Drafting the note from the attempt log…" : state}</p>
          {draft && <DraftEditor draft={draft} attemptId={attemptId} onSaved={setNote} />}
        </>
      )}
    </section>
  );
}
