import { useState } from "react";
import { Link } from "react-router-dom";
import { API } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

const day = (iso) => new Date(iso).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
export const noteHeader = (n) => `${n.client_name} · ${day(n.attempt_date)} · ${n.route_name} v${n.route_version}`;

function NoteRow({ n }) {
  const [msg, setMsg] = useState("");
  const p = `client-note-${n.id}`;
  const copy = () => navigator.clipboard.writeText(`${noteHeader(n)}\n\n${n.text}`).then(() => setMsg("Copied")).catch(() => setMsg("Couldn't copy"));
  return (
    <li className="bv-note-row" data-testid={p}>
      <p className="bv-strong">{day(n.attempt_date)} · {n.route_name} · v{n.route_version}</p>
      <p>By {n.author}</p>
      <div className="bv-btn-row">
        <button type="button" className="bv-btn" onClick={copy} data-testid={`${p}-copy`}>Copy</button>
        <Link to={`/notes/${n.id}/print`} target="_blank" className="bv-btn" data-testid={`${p}-print`}>Print</Link>
        <span role="status" aria-live="polite" className="bv-strong" data-testid={`${p}-copy-status`}>{msg}</span>
      </div>
    </li>
  );
}

export default function ClientNotes({ clientId }) {
  const { status, data } = useApi(`${API}/clients/${clientId}/notes`);
  return (
    <section aria-labelledby="progress-notes-heading" className="bv-panel" data-testid="client-progress-notes">
      <h2 id="progress-notes-heading" className="bv-h2">Progress notes</h2>
      {status === "error" && <p className="bv-error" role="status">Couldn't load progress notes</p>}
      {status === "ready" && (data.length === 0 ? <p data-testid="client-progress-notes-empty">No progress notes yet.</p> : (
        <ul className="bv-notes" data-testid="client-progress-notes-list">{data.map((n) => <NoteRow key={n.id} n={n} />)}</ul>
      ))}
    </section>
  );
}
