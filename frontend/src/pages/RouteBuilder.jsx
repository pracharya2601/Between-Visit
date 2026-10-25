import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import CheckpointCard from "@/components/CheckpointCard";
import { saveBlocker } from "@/lib/saveBlocker";
import VersionHistory from "@/components/review/VersionHistory";
import ReplayLauncher from "@/components/replay/ReplayLauncher";

export default function RouteBuilder() {
  const { id } = useParams();
  const [route, setRoute] = useState(null);
  const [cps, setCps] = useState([]);
  const [name, setName] = useState("");
  const [loadError, setLoadError] = useState("");
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const nameTimer = useRef(null);

  useEffect(() => {
    let alive = true;
    axios.get(`${API}/routes/${id}`)
      .then((r) => { if (alive) { setRoute(r.data); setName(r.data.name); setCps(r.data.checkpoints); } })
      .catch((e) => alive && setLoadError(e.response?.status === 404 ? "Route not found" : "Couldn't load practice data"));
    return () => { alive = false; };
  }, [id]);

  const saveName = (value) => axios.patch(`${API}/routes/${id}`, { name: value }).then((r) => setRoute(r.data));
  const onName = (value) => {
    setName(value);
    clearTimeout(nameTimer.current);
    if (!value.trim()) return setStatus("A route needs a name. The last saved name is kept until you type a new one.");
    nameTimer.current = setTimeout(() => saveName(value).catch(() => setStatus("Couldn't save the route name.")), 500);
  };
  const replace = (cp) => setCps((list) => list.map((c) => (c.id === cp.id ? cp : c)));

  const act = async (fn, okMsg, failMsg) => {
    try { await fn(); setStatus(okMsg); } catch { setStatus(failMsg); }
  };
  const onAdd = () => act(async () => {
    const r = await axios.post(`${API}/routes/${id}/checkpoints`);
    setCps((list) => [...list, r.data]);
  }, `Checkpoint ${cps.length + 1} added`, "Couldn't add a checkpoint.");
  const onMove = (cpId, direction) => act(async () => {
    const r = await axios.post(`${API}/checkpoints/${cpId}/move`, { direction });
    setCps(r.data);
  }, `Checkpoint moved ${direction}`, "Couldn't move the checkpoint.");
  const onRemove = (cpId) => act(async () => {
    await axios.delete(`${API}/checkpoints/${cpId}`);
    setCps((list) => list.filter((c) => c.id !== cpId).map((c, i) => ({ ...c, order: i + 1 })));
  }, "Checkpoint removed", "Couldn't remove the checkpoint.");

  const onSave = async () => {
    setSaving(true);
    setStatus("Saving…");
    try {
      clearTimeout(nameTimer.current);
      await saveName(name);
      const r = await axios.post(`${API}/routes/${id}/save`);
      setRoute((rt) => ({ ...rt, current_version: r.data.version }));
      setStatus(`Saved as version ${r.data.version}`);
    } catch (e) {
      const d = e.response?.data?.detail;
      setStatus(`Couldn't save the route. ${typeof d === "string" ? d : "Try again."}`);
    } finally {
      setSaving(false);
    }
  };

  if (loadError || !route) {
    return (
      <div aria-live="polite" role="status" data-testid="builder-load-status">
        {loadError ? <p className="bv-error">{loadError}</p> : <p>Loading route…</p>}
      </div>
    );
  }

  const blocker = saveBlocker(name, cps);
  return (
    <div className="bv-stack">
      <p><Link to="/routes" className="bv-link" data-testid="back-to-routes-link">Back to routes</Link></p>
      <section aria-labelledby="builder-heading">
        <p className="bv-eyebrow" data-testid="builder-version">
          Route builder · {route.current_version > 0 ? `Version ${route.current_version}` : "Not saved yet"}
        </p>
        <h1 id="builder-heading" className="bv-h1">{name || "New route"}</h1>
        {route.current_version >= 1 && (
          <Link to={`/routes/${id}/assign`} className="bv-btn bv-btn-primary bv-btn-link" data-testid="assign-exercise-button">Assign exercise</Link>
        )}
      </section>
      <div className="bv-field">
        <label htmlFor="route-name" className="bv-label">Route name</label>
        <input id="route-name" className="bv-input" value={name} onChange={(e) => onName(e.target.value)} data-testid="route-name-input" />
      </div>
      <section aria-labelledby="checkpoints-heading">
        <h2 id="checkpoints-heading" className="bv-h2">Checkpoints ({cps.length})</h2>
        <ol className="bv-cp-list" data-testid="checkpoint-list">
          {cps.map((cp, i) => (
            <CheckpointCard key={cp.id} cp={cp} index={i} total={cps.length} onChange={replace} onMove={onMove} onRemove={onRemove} />
          ))}
        </ol>
        <button type="button" className="bv-btn" onClick={onAdd} data-testid="add-checkpoint-button">Add checkpoint</button>
      </section>
      <section className="bv-panel" aria-labelledby="save-heading">
        <h2 id="save-heading" className="bv-h2">Save</h2>
        {blocker && <p id="save-reason" data-testid="save-disabled-reason">{blocker}</p>}
        <button type="button" className="bv-btn bv-btn-primary" disabled={!!blocker || saving} aria-describedby={blocker ? "save-reason" : undefined} onClick={onSave} data-testid="save-route-button">
          Save route
        </button>
        <p aria-live="polite" role="status" className="bv-cp-msg" data-testid="save-status">{status}</p>
      </section>
      {route.current_version >= 1 && <ReplayLauncher routeId={id} />}
      {route.current_version >= 1 && <VersionHistory routeId={id} refreshToken={route.current_version} />}
    </div>
  );
}
