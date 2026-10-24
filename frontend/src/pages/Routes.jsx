import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

export default function RoutesPage() {
  const { status, data } = useApi(`${API}/routes`);
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const onNew = async () => {
    setCreating(true);
    setError("");
    try {
      const r = await axios.post(`${API}/routes`);
      navigate(`/routes/${r.data.id}`);
    } catch {
      setError("Couldn't create a route. Try again.");
      setCreating(false);
    }
  };

  return (
    <div className="bv-stack">
      <section aria-labelledby="routes-heading" className="bv-title-row">
        <div>
          <p className="bv-eyebrow">Workspace</p>
          <h1 id="routes-heading" className="bv-h1">Routes</h1>
        </div>
        <button type="button" className="bv-btn bv-btn-primary bv-btn-inline" onClick={onNew} disabled={creating} data-testid="new-route-button">
          New route
        </button>
      </section>
      <div aria-live="polite" role="status" data-testid="routes-status">
        {status === "loading" && <p>Loading routes…</p>}
        {status === "error" && <p className="bv-error">Couldn't load practice data</p>}
        {error && <p className="bv-error">{error}</p>}
      </div>
      {status === "ready" && (
        data.length === 0 ? <p>No routes yet.</p> : (
          <ul className="bv-rows" data-testid="routes-list">
            {data.map((r) => (
              <li key={r.id}>
                <Link to={`/routes/${r.id}`} className="bv-row-link" data-testid={`route-link-${r.id}`}>
                  <span className="bv-row-title">{r.name || "Untitled route"}</span>
                  <span className="bv-row-meta">
                    {r.checkpoint_count} {r.checkpoint_count === 1 ? "checkpoint" : "checkpoints"} ·{" "}
                    {r.current_version > 0 ? `Version ${r.current_version}` : "Version 0 (Not saved yet)"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}
