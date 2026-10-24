import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";

export default function TeachStartForm() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return setError("Enter a route name first.");
    setBusy(true);
    setError("");
    try {
      const r = await axios.post(`${API}/teach`, { route_name: name.trim() });
      navigate(`/teach/${r.data.id}`);
    } catch {
      setError("Couldn't start a teach walk. Try again.");
      setBusy(false);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="bv-panel" aria-labelledby="teach-heading" data-testid="teach-start-form">
      <h2 id="teach-heading" className="bv-h2">Teach by walking</h2>
      <p>Walk the route wearing GlassCam with the iPhone. The server proposes checkpoints and builds a 3D map.</p>
      <label htmlFor="teach-route-name" className="bv-label">Route name</label>
      <div className="bv-copy-row">
        <input id="teach-route-name" className="bv-input" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={!!error || undefined} aria-describedby={error ? "teach-error" : undefined} data-testid="teach-route-name-input" />
        <button type="submit" className="bv-btn bv-btn-primary bv-btn-inline" disabled={busy} data-testid="teach-start-button">Teach by walking</button>
      </div>
      <p id="teach-error" role="status" aria-live="polite" className="bv-error-text" data-testid="teach-start-error">{error}</p>
    </form>
  );
}
