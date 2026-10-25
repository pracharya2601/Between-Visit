import { lazy, Suspense, useCallback, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";
import { PlacementLayer } from "@/components/scan/PlacementLayer";
import { PlacementList, facingOf } from "@/components/scan/PlacementList";

const Scene3D = lazy(() => import("@/components/teach/Scene3D"));
const errText = (e, fallback) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : fallback);
const UNITS = { m: "metres", cm: "centimetres", mm: "millimetres" };

function ScanFacts({ scan, busy, onUnit, onUpright }) {
  return (
    <section className="bv-panel" aria-labelledby="scan-facts-heading" data-testid="scan-facts">
      <h2 id="scan-facts-heading" className="bv-h2">The scan</h2>
      <p data-testid="scan-size">Measured size: {scan.dimensions?.text}</p>
      <p className="bv-hint" data-testid="scan-points">{scan.point_count.toLocaleString()} points · colours from {scan.colour_source || "height (the file has no colours)"}</p>
      <div className="bv-btn-row">
        <label className="bv-label" htmlFor="scan-unit">The file is in
          <select id="scan-unit" className="bv-input" value={scan.unit} disabled={busy} onChange={(e) => onUnit(e.target.value)} data-testid="scan-unit-select">
            {Object.entries(UNITS).map(([k, v]) => <option key={k} value={k}>{v}{k === scan.auto_unit ? " (detected)" : ""}</option>)}
          </select>
        </label>
        <button type="button" className="bv-btn" disabled={busy} onClick={onUpright} data-testid="scan-turn-upright-button">Turn upright</button>
      </div>
      <p className="bv-hint" data-testid="scan-up-axis">Up axis: {scan.up}{scan.up === scan.auto_up ? " (detected)" : ""}. If the floor isn't at the bottom, press Turn upright.</p>
    </section>
  );
}

export default function ScanPlacement({ scan, onScan }) {
  const [points, setPoints] = useState([]);
  const [facing, setFacing] = useState(null);
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const snapshot = useCallback(() => setHistory((h) => [...h.slice(-49), { points, facing }]), [points, facing]);
  const change = (nextPoints, nextFacing = facing) => { snapshot(); setPoints(nextPoints); setFacing(nextFacing); };
  const onPlaceEntrance = (x, z) => { change([{ name: "Entrance", x, z }], null); setSelected(0); setMsg("Entrance placed. Drag to set the facing."); };
  const onFacing = (f) => setFacing(f);
  const onAdd = (x, z) => { change([...points, { name: `Checkpoint ${points.length + 1}`, x, z }]); setSelected(points.length); setMsg(`Checkpoint ${points.length + 1} placed`); };
  const onMovePoint = (i, x, z) => setPoints((l) => l.map((p, j) => (j === i ? { ...p, x, z } : p)));
  const onEdit = (i, fields) => change(points.map((p, j) => (j === i ? { ...p, ...fields } : p)));
  const onRemove = (i) => { change(points.filter((_, j) => j !== i)); setSelected(null); setMsg(`Checkpoint ${i + 1} removed`); };
  const onUndo = () => { const last = history[history.length - 1]; if (!last) return; setHistory((h) => h.slice(0, -1)); setPoints(last.points); setFacing(last.facing); setMsg("Undone"); };
  const onAddAhead = () => {
    const last = points[points.length - 1], prev = points[points.length - 2];
    const d = prev ? [last.x - prev.x, last.z - prev.z] : facing;
    const len = Math.hypot(d[0], d[1]) || 1;
    onAdd(last.x + (d[0] / len) * 2, last.z + (d[1] / len) * 2);
  };
  const onDragEnd = useCallback(() => snapshot(), [snapshot]);

  const orient = async (body) => {
    setBusy(true);
    try { onScan((await axios.post(`${API}/scans/${scan.id}/orient`, body)).data); setPoints([]); setFacing(null); setHistory([]); }
    catch (e) { setMsg(errText(e, "That didn't work. Try again.")); }
    finally { setBusy(false); }
  };
  const confirm = async () => {
    setBusy(true);
    setMsg("Re-centring the model on the Entrance…");
    try { onScan((await axios.post(`${API}/scans/${scan.id}/place`, { facing, points })).data); }
    catch (e) { setMsg(errText(e, "Couldn't confirm the placement. Try again.")); setBusy(false); }
  };

  const blocker = !points.length ? "Place the Entrance first." : !facing ? "Drag from the Entrance to set the facing." : points.length < 2 ? "Place at least one checkpoint after the Entrance." : "";
  const key = `${scan.unit}-${scan.up}`;
  return (
    <div className="bv-review">
      <div className="bv-review-scene">
        <Suspense fallback={<p>Loading the 3D view…</p>}>
          <Scene3D key={key} scene={scan.scene} pointsUrl={`${API}/scans/${scan.id}/points?v=${key}`} colorsUrl={scan.colour_source ? `${API}/scans/${scan.id}/colors?v=${key}` : null}
            interactive testId="scan-scene" label="3D scan. Click the floor to place the Entrance, drag to set the facing, click again to add checkpoints. The list next to it does the same with the keyboard."
            hint="Click the floor: Entrance, then drag to set facing. Click again: next checkpoint. Drag a marker to move it. Drag empty space to orbit.">
            <PlacementLayer points={points} facing={facing} selected={selected} onPlaceEntrance={onPlaceEntrance} onFacing={onFacing} onAdd={onAdd}
              onMovePoint={onMovePoint} onSelect={setSelected} onDragEnd={onDragEnd} />
          </Scene3D>
        </Suspense>
      </div>
      <div className="bv-stack">
        <ScanFacts scan={scan} busy={busy} onUnit={(unit) => orient({ unit })} onUpright={() => orient({ turn_upright: true })} />
        <PlacementList points={points} facing={facing} selected={selected} onEdit={onEdit} onRemove={onRemove} onSelect={setSelected}
          onFacingDeg={(deg) => change(points, facingOf(deg))} onAddAhead={onAddAhead} onUndo={onUndo} canUndo={history.length > 0} />
        <section className="bv-panel" aria-labelledby="placement-confirm-heading">
          <h2 id="placement-confirm-heading" className="bv-h2">Confirm placement</h2>
          {blocker && <p id="placement-blocker" data-testid="placement-blocker">{blocker}</p>}
          <button type="button" className="bv-btn bv-btn-primary" disabled={busy || !!blocker} aria-describedby={blocker ? "placement-blocker" : undefined} onClick={confirm} data-testid="placement-confirm-button">Confirm placement</button>
          <p role="status" aria-live="polite" className="bv-cp-msg" data-testid="placement-status">{msg}</p>
        </section>
      </div>
    </div>
  );
}
