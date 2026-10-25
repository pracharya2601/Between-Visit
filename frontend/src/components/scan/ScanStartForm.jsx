import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";

const MAX_BYTES = 100 * 1024 * 1024;
const CHUNK = 8 * 1024 * 1024;
const EXTS = [".glb", ".ply", ".obj"];
const errText = (e, fallback) => (typeof e.response?.data?.detail === "string" ? e.response.data.detail : fallback);

export async function uploadScan(file, routeName, onProgress, stopped = () => false) {
  const r = await axios.post(`${API}/scans`, { route_name: routeName, empty_space: true, filename: file.name, size: file.size });
  const id = r.data.id;
  try {
    for (let off = 0; off < file.size; off += CHUNK) {
      if (stopped()) throw new Error("Upload cancelled. Nothing was kept.");
      await axios.put(`${API}/scans/${id}/chunk?offset=${off}`, file.slice(off, off + CHUNK), { headers: { "Content-Type": "application/octet-stream" } });
      onProgress(Math.min(file.size, off + CHUNK) / file.size);
    }
    onProgress(1, "processing");
    await axios.post(`${API}/scans/${id}/process`, null, { timeout: 180000 });
  } catch (e) {
    axios.post(`${API}/scans/${id}/cancel`).catch(() => {});
    throw e;
  }
  return id;
}

export default function ScanStartForm() {
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const stopRef = useRef(false);
  const [name, setName] = useState("");
  const [empty, setEmpty] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(null);

  const pick = (e) => {
    const f = e.target.files?.[0] || null;
    setError("");
    if (f && !EXTS.some((x) => f.name.toLowerCase().endsWith(x))) { e.target.value = ""; setFile(null); return setError("Choose a .glb, .ply or .obj file."); }
    if (f && f.size > MAX_BYTES) { e.target.value = ""; setFile(null); return setError("This file is over 100 MB. Export a smaller scan (lower detail or a shorter area)."); }
    setFile(f);
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return setError("Enter a route name first.");
    if (!empty) return setError("Tick “I scanned an empty space (no people)” before uploading.");
    if (!file) return setError("Choose a 3D scan file.");
    setError("");
    setProgress({ pct: 0, phase: "uploading" });
    try {
      const id = await uploadScan(file, name.trim(), (p, phase = "uploading") => setProgress({ pct: Math.round(p * 100), phase }), () => stopRef.current);
      navigate(`/scan/${id}`);
    } catch (err) {
      setProgress(null);
      setError(stopRef.current ? "Upload cancelled. Nothing was kept." : errText(err, "The upload didn't work. Try again."));
      stopRef.current = false;
    }
  };

  const busy = !!progress;
  const statusText = !progress ? "" : progress.phase === "processing" ? "Turning the scan into points… this can take up to a minute." : `Uploading… ${progress.pct}%`;
  return (
    <form onSubmit={onSubmit} noValidate className="bv-panel" aria-labelledby="scan-heading" data-testid="scan-start-form">
      <h2 id="scan-heading" className="bv-h2">Create from 3D scan</h2>
      <p>Upload a phone scan of the route (Polycam, Scaniverse or 3D Scanner App). Then place the Entrance and the checkpoints on it.</p>
      <label htmlFor="scan-route-name" className="bv-label">Route name</label>
      <input id="scan-route-name" className="bv-input" value={name} onChange={(e) => setName(e.target.value)} disabled={busy} data-testid="scan-route-name-input" />
      <label className="bv-check" htmlFor="scan-empty-space">
        <input id="scan-empty-space" type="checkbox" checked={empty} onChange={(e) => setEmpty(e.target.checked)} disabled={busy} required data-testid="scan-empty-space-checkbox" />
        <span>I scanned an empty space (no people)</span>
      </label>
      <label htmlFor="scan-file" className="bv-label">3D scan file (.glb best, also .ply or .obj, up to 100 MB)</label>
      <input id="scan-file" ref={fileRef} type="file" accept=".glb,.ply,.obj" className="bv-file" onChange={pick} disabled={busy || !empty} aria-describedby="scan-file-gate" data-testid="scan-file-input" />
      {!empty && <p id="scan-file-gate" className="bv-hint" data-testid="scan-file-gate">Tick the box above to choose a file.</p>}
      <div className="bv-btn-row">
        <button type="submit" className="bv-btn bv-btn-primary" disabled={busy || !empty} data-testid="scan-upload-button">Upload scan</button>
        {progress?.phase === "uploading" && <button type="button" className="bv-btn" onClick={() => { stopRef.current = true; }} data-testid="scan-upload-cancel-button">Cancel upload</button>}
      </div>
      {progress && progress.phase === "uploading" && <progress className="bv-progress" max={100} value={progress.pct} aria-label="Upload progress" data-testid="scan-upload-progress" />}
      <p role="status" aria-live="polite" className="bv-cp-msg" data-testid="scan-upload-status">{statusText}</p>
      <p role="alert" className="bv-error-text" data-testid="scan-upload-error">{error}</p>
    </form>
  );
}
