import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";
import MachineView from "@/components/review/MachineView";

const hhmm = (iso) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

function KnownEntity({ e, routeId, onRemoved }) {
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const p = `known-entity-${e.id}`;
  const remove = () => axios.post(`${API}/routes/${routeId}/known-entities/${e.id}/remove`)
    .then(onRemoved).catch(() => setError("Couldn't remove it. Try again."));
  return (
    <li data-testid={p}>
      <span className="bv-strong">{e.label}</span> ({e.side}, between checkpoints {e.segment?.from} and {e.segment?.to}
      {e.position ? "" : ", no position"}) · added in v{e.added_in}
      {!asking ? (
        <button type="button" className="bv-btn bv-btn-small" onClick={() => setAsking(true)} data-testid={`${p}-remove-button`}>Remove from memory</button>
      ) : (
        <span className="bv-btn-row" role="group" aria-label={`Remove ${e.label}?`}>
          <span>Remove {e.label} from the route memory? This makes a new version.</span>
          <button type="button" className="bv-btn bv-btn-small bv-btn-danger" onClick={remove} data-testid={`${p}-remove-confirm`}>Yes, remove</button>
          <button type="button" className="bv-btn bv-btn-small" onClick={() => setAsking(false)} data-testid={`${p}-remove-cancel`}>Cancel</button>
        </span>
      )}
      {error && <span role="alert" className="bv-error"> {error}</span>}
      {e.machine && <MachineView machine={e.machine} testId={`${p}-machine`} />}
    </li>
  );
}

export default function VersionHistory({ routeId, refreshToken, onChanged }) {
  const [h, setH] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => axios.get(`${API}/routes/${routeId}/history`).then((r) => setH(r.data)).catch(() => setError("Couldn't load the version history")), [routeId]);
  useEffect(() => { load(); }, [load, refreshToken]);
  const removed = () => { load(); onChanged?.(); };

  return (
    <section className="bv-panel" aria-labelledby="history-heading" data-testid="version-history">
      <h2 id="history-heading" className="bv-h2">Version history</h2>
      {error && <p role="alert" className="bv-error">{error}</p>}
      {h && (
        <>
          <ol className="bv-history" reversed data-testid="version-history-list">
            {h.versions.map((v) => (
              <li key={v.version} data-testid={`version-history-v${v.version}`}>v{v.version}: {v.note} by {v.author}, {hhmm(v.created_at)}</li>
            ))}
          </ol>
          <h3 className="bv-h3">Known objects in v{h.current_version}</h3>
          {h.known_entities.length === 0 ? <p data-testid="known-entities-empty">None yet.</p> : (
            <ul className="bv-known" data-testid="known-entities-list">
              {h.known_entities.map((e) => <KnownEntity key={e.id} e={e} routeId={routeId} onRemoved={removed} />)}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
