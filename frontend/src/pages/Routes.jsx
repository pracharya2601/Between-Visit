import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import { useApi } from "@/hooks/useApi";
import TeachStartForm from "@/components/teach/TeachStartForm";

export default function RoutesPage() {
  useTitle("Routes");
  const { status, data } = useApi(`${API}/routes`);
  const navigate = useNavigate();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");

  const onNew = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return setError("Enter a route name first.");
    setCreating(true);
    setError("");
    try {
      const r = await axios.post(`${API}/routes`, { name: newName.trim() });
      navigate(`/routes/${r.data.id}`);
    } catch {
      setError("Couldn't create a route. Try again.");
      setCreating(false);
    }
  };

  return (
    <div className="bv-stack">
      <section aria-labelledby="routes-heading">
        <p className="bv-eyebrow">Workspace</p>
        <h1 id="routes-heading" className="bv-h1">Routes</h1>
      </section>
      <form onSubmit={onNew} noValidate className="bv-panel" aria-labelledby="new-route-heading" data-testid="new-route-form">
        <h2 id="new-route-heading" className="bv-h2">New route</h2>
        <label htmlFor="new-route-name" className="bv-label">Route name</label>
        <div className="bv-copy-row">
          <input id="new-route-name" className="bv-input" value={newName} onChange={(e) => setNewName(e.target.value)} aria-invalid={!!error || undefined} data-testid="new-route-name-input" />
          <button type="submit" className="bv-btn bv-btn-primary bv-btn-inline" disabled={creating} data-testid="new-route-button">Create route</button>
        </div>
      </form>
      <TeachStartForm />
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
