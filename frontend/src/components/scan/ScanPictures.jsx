import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { saveBlocker } from "@/lib/saveBlocker";
import { useSimilarity } from "@/lib/useSimilarity";
import { renderViews } from "@/lib/scanRender";
import CheckpointCard from "@/components/CheckpointCard";

const Scene3D = lazy(() => import("@/components/teach/Scene3D"));
const errText = (e, fallback) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : fallback);

export default function ScanPictures({ scan }) {
  const [cps, setCps] = useState([]);
  const [status, setStatus] = useState("");
  const [rendering, setRendering] = useState(false);
  const [saved, setSaved] = useState(null);
  const alike = useSimilarity(cps);
  const started = useRef(false);
  const pointsUrl = `${API}/scans/${scan.id}/points?v=placed`;
  const colorsUrl = scan.colour_source ? `${API}/scans/${scan.id}/colors?v=placed` : null;

  const load = useCallback(async () => {
    const r = await axios.get(`${API}/routes/${scan.route_id}`).catch(() => null);
    const list = r ? r.data.checkpoints : [];
    setCps(list);
    return list;
  }, [scan.route_id]);

  const render = useCallback(async (list, only) => {
    setRendering(true);
    try {
      const files = await renderViews(pointsUrl, colorsUrl, scan.scene.checkpoints);
      for (let i = 0; i < list.length; i++) {
        if (only && !only(list[i])) continue;
        setStatus(`Rendering and checking picture ${i + 1} of ${list.length}…`);
        const form = new FormData();
        form.append("file", files[i]);
        try {
          const r = await axios.post(`${API}/checkpoints/${list[i].id}/photo`, form);
          setCps((l) => l.map((c) => (c.id === r.data.checkpoint.id ? r.data.checkpoint : c)));
        } catch (e) {
          setStatus(errText(e, `Couldn't add picture ${i + 1}.`));
        }
      }
      setStatus("Pictures ready. Check each one, replace it with a photo if you like, then approve.");
    } catch {
      setStatus("Couldn't render the pictures in this browser. Use Take photo or Upload photo for each checkpoint.");
    } finally { setRendering(false); }
  }, [pointsUrl, colorsUrl, scan.scene.checkpoints]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    load().then((list) => list.some((c) => !c.photo_url) && render(list, (c) => !c.photo_url));
  }, [load, render]);

  const replace = (cp) => setCps((l) => l.map((c) => (c.id === cp.id ? cp : c)));
  const onSave = async () => {
    try { setSaved((await axios.post(`${API}/scans/${scan.id}/save`)).data); setStatus("Saved as version 1"); }
    catch (e) { setStatus(errText(e, "Couldn't save. Try again.")); }
  };
  const blocker = saved ? "" : rendering ? "Wait for the pictures to finish." : saveBlocker(scan.route_name, cps);

  return (
    <div className="bv-review">
      <div className="bv-review-scene">
        <Suspense fallback={<p>Loading the 3D view…</p>}>
          <Scene3D scene={scan.scene} pointsUrl={pointsUrl} colorsUrl={colorsUrl} testId="scan-placed-scene"
            label={`3D scan re-centred on the Entrance, with ${scan.scene.checkpoints.length} checkpoints along a ${scan.scene.metres_walked} metre route. The checkpoint list gives the same information.`} />
        </Suspense>
      </div>
      <section aria-labelledby="scan-cps-heading" className="bv-review-list">
        <h2 id="scan-cps-heading" className="bv-h2">Checkpoint pictures ({cps.length})</h2>
        <p className="bv-hint">Each picture is the 3D view at eye height (1.6 m), facing the next checkpoint. AI suggests the landmark text.</p>
        <p role="status" aria-live="polite" className="bv-cp-msg" data-testid="scan-render-status">{status}</p>
        <button type="button" className="bv-btn" disabled={rendering || !!saved} onClick={() => render(cps)} data-testid="scan-rerender-button">Render all pictures again</button>
        <ol className="bv-cp-list" data-testid="scan-checkpoint-list">
          {cps.map((cp, i) => <CheckpointCard key={cp.id} cp={cp} index={i} total={cps.length} onChange={replace} alike={alike[cp.id]} />)}
        </ol>
        <section className="bv-panel" aria-labelledby="scan-save-heading">
          <h2 id="scan-save-heading" className="bv-h2">Save</h2>
          {blocker && <p id="scan-save-reason" data-testid="scan-save-reason">{blocker}</p>}
          {saved ? (
            <p data-testid="scan-saved">Saved version {saved.version} with the {saved.label}. <Link to={`/routes/${saved.route_id}`} className="bv-link" data-testid="scan-open-route-link">Open the saved route</Link></p>
          ) : (
            <button type="button" className="bv-btn bv-btn-primary" disabled={!!blocker} aria-describedby={blocker ? "scan-save-reason" : undefined} onClick={onSave} data-testid="scan-save-button">Save route</button>
          )}
        </section>
      </section>
    </div>
  );
}
