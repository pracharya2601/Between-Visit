import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import { saveBlocker } from "@/lib/saveBlocker";
import CheckpointCard from "@/components/CheckpointCard";

const Scene3D = lazy(() => import("@/components/teach/Scene3D"));

export default function TeachReview() {
  useTitle("Review taught checkpoints");
  const { id } = useParams();
  const [session, setSession] = useState(null);
  const [scene, setScene] = useState(null);
  const [cps, setCps] = useState([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [saved, setSaved] = useState(null);

  const loadCps = useCallback((routeId) => axios.get(`${API}/routes/${routeId}`).then((r) => setCps(r.data.checkpoints)), []);
  useEffect(() => {
    axios.get(`${API}/teach/${id}`).then(async (r) => {
      setSession(r.data);
      if (r.data.status !== "finished" || r.data.saved) return setError("This walk isn't waiting for review.");
      await loadCps(r.data.route_id);
      setScene((await axios.get(`${API}/teach/${id}/scene`)).data);
    }).catch(() => setError("Teach walk not found"));
  }, [id, loadCps]);

  const pending = cps.some((c) => c.photo_pending);
  useEffect(() => {
    if (!pending || !session) return;
    const t = setInterval(() => loadCps(session.route_id).catch(() => {}), 2000);
    return () => clearInterval(t);
  }, [pending, session, loadCps]);

  const act = async (fn, ok) => { try { await fn(); setStatus(ok); } catch { setStatus("That didn't work. Try again."); } };
  const replace = (cp) => setCps((l) => l.map((c) => (c.id === cp.id ? cp : c)));
  const onMove = (cpId, direction) => act(async () => setCps((await axios.post(`${API}/checkpoints/${cpId}/move`, { direction })).data), `Checkpoint moved ${direction}`);
  const onRemove = (cpId) => act(async () => {
    await axios.delete(`${API}/checkpoints/${cpId}`);
    setCps((l) => l.filter((c) => c.id !== cpId).map((c, i) => ({ ...c, order: i + 1 })));
  }, "Checkpoint removed");
  const onSave = () => act(async () => {
    const r = await axios.post(`${API}/teach/${id}/save`);
    setSaved(r.data);
  }, "Saved as version 1");

  if (error || !session) return <div role="status" aria-live="polite">{error ? <p className="bv-error" data-testid="review-error">{error}</p> : <p>Loading the walk…</p>}</div>;
  const blocker = saved ? "" : pending ? "Wait for the photos to finish." : saveBlocker(session.route_name, cps);

  return (
    <div className="bv-stack">
      <section aria-labelledby="review-heading">
        <p className="bv-eyebrow">Review walk · {session.route_name}</p>
        <h1 id="review-heading" className="bv-h1">Review the walk</h1>
      </section>
      <div className="bv-review">
        <div className="bv-review-scene">
          {scene ? <Suspense fallback={<p>Loading the 3D view…</p>}><Scene3D scene={scene} pointsUrl={`${API}/teach/${id}/points`} /></Suspense> : <p>Loading the 3D view…</p>}
        </div>
        <section aria-labelledby="review-list-heading" className="bv-review-list">
          <h2 id="review-list-heading" className="bv-h2">Checkpoints ({cps.length})</h2>
          <ol className="bv-cp-list" data-testid="review-checkpoint-list">
            {cps.map((cp, i) => <CheckpointCard key={cp.id} cp={cp} index={i} total={cps.length} onChange={replace} onMove={onMove} onRemove={onRemove} />)}
          </ol>
          <section className="bv-panel" aria-labelledby="review-save-heading">
            <h2 id="review-save-heading" className="bv-h2">Save</h2>
            {blocker && <p id="review-save-reason" data-testid="review-save-reason">{blocker}</p>}
            {saved ? (
              <p><Link to={`/routes/${saved.route_id}`} className="bv-link" data-testid="review-open-route-link">Open the saved route</Link></p>
            ) : (
              <button type="button" className="bv-btn bv-btn-primary" disabled={!!blocker} aria-describedby={blocker ? "review-save-reason" : undefined} onClick={onSave} data-testid="review-save-button">Save route</button>
            )}
            <p role="status" aria-live="polite" className="bv-cp-msg" data-testid="review-save-status">{status}</p>
          </section>
        </section>
      </div>
    </div>
  );
}
