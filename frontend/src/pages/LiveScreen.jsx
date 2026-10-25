import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import Replay3D, { Legend3D } from "@/components/replay/Replay3D";

function useLive(id) {
  const [s, setS] = useState(null);
  useEffect(() => {
    let alive = true, t;
    const poll = async () => {
      try {
        const r = await axios.get(`${API}/attempts/${id}/live`);
        if (!alive) return;
        setS(r.data);
        if (r.data.status === "ended") return;
      } catch (e) {
        if (e.response?.status === 404) return alive && setS({ missing: true });
      }
      t = setTimeout(poll, 1000);
    };
    poll();
    return () => { alive = false; clearTimeout(t); };
  }, [id]);
  return s;
}

function useTick(ms, on) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!on) return undefined;
    const t = setInterval(() => setN((v) => v + 1), ms);
    return () => clearInterval(t);
  }, [ms, on]);
  return n;
}

function LivePicture({ s, tick }) {
  const [src, setSrc] = useState(null);
  const url = useRef(null);
  useEffect(() => {
    if (!s.frame_url) { setSrc(null); return; }
    fetch(`${process.env.REACT_APP_BACKEND_URL}${s.frame_url}`, { cache: "no-store" })
      .then((r) => (r.status === 200 ? r.blob() : null))
      .then((b) => {
        if (url.current) URL.revokeObjectURL(url.current);
        url.current = b ? URL.createObjectURL(b) : null;
        setSrc(url.current);
      }).catch(() => {});
  }, [s.frame_url, tick]);
  useEffect(() => () => url.current && URL.revokeObjectURL(url.current), []);
  return (
    <div className="bv-live-picture" data-testid="live-picture">
      {src ? <img src={src} alt="Newest picture from the client's glasses (not stored)" data-testid="live-picture-image" /> : <p>No live picture right now.</p>}
    </div>
  );
}

function summary(s) {
  return `Live run on ${s.route_name}. Last checkpoint: ${s.last_checkpoint ?? "none yet"}. Reached: ${(s.reached_checkpoints || []).join(", ") || "none yet"}. Cues so far: ${s.cues_spoken} spoken, ${s.cues_held_back} held back. Latest spoken: ${s.caption?.text ?? "nothing yet"}.`;
}

function Stage({ s }) {
  const [freeLook, setFreeLook] = useState(false);
  const active = s.status === "running" || s.status === "paused";
  const tick = useTick(1000, active);
  const pointsTick = useTick(3000, active && !s.saved_model);
  return (
    <div className="bv-replay bv-replay-3dmode" data-testid="live-stage">
      <div className="bv-replay-main">
        <Replay3D three={s.three} pointsBase={`${API}/attempts/${s.attempt_id}/live/points`} pointsKey={s.saved_model ? null : String(pointsTick)} freeLook={freeLook}
          reached={s.reached_checkpoints || []} testId="live-scene" what={s.saved_model ? `the saved route model with the live trail` : s.three.scene.grid ? "a floor grid with the live trail (no depth from this phone)" : "the 3D points measured live during this run"} />
        <p className="bv-sr-only" data-testid="live-3d-summary">{summary(s)}</p>
      </div>
      <div className="bv-replay-right">
        <LivePicture s={s} tick={tick} />
        <p role="status" aria-live="polite" className={`bv-badge ${s.live ? "bv-badge-live" : ""}`} data-testid="live-connection">{s.status === "ended" ? "Run ended" : s.live ? "Live" : "Not connected"}</p>
        <p data-testid="live-last-checkpoint">Last checkpoint: <span className="bv-strong">{s.last_checkpoint ?? "none yet"}</span></p>
        <p data-testid="live-counts">Cues spoken: {s.cues_spoken} · held back: {s.cues_held_back}</p>
        <p className="bv-row-meta" data-testid="live-model-line">{s.saved_model ? "Saved route model" : s.three.scene.grid ? "No depth yet: trail on a floor grid" : `${s.three.scene.points.toLocaleString()} live points (dropped when the run ends)`}</p>
        <Legend3D />
        <label className="bv-choice">
          <input type="checkbox" checked={freeLook} onChange={(e) => setFreeLook(e.target.checked)} data-testid="live-free-look-toggle" />
          <span>Free look</span>
        </label>
        {s.review_path && <Link to={s.review_path} className="bv-link bv-strong" data-testid="live-review-link">Run ended. Open the review</Link>}
      </div>
      <p className="bv-replay-caption" aria-live="assertive" role="status" data-testid="live-caption">{s.caption?.text ?? " "}</p>
    </div>
  );
}

export default function LiveScreen() {
  const { id } = useParams();
  useTitle("Watch live");
  const s = useLive(id);
  return (
    <div className="bv-replay-page" data-testid="live-screen">
      <h1 className="bv-replay-title" data-testid="live-title">Watch live{s?.route_name ? `: ${s.route_name}` : ""}</h1>
      {!s && <p role="status">Connecting…</p>}
      {s?.missing && <p className="bv-error" role="status" data-testid="live-not-found">Run not found.</p>}
      {s && !s.missing && <Stage s={s} />}
    </div>
  );
}
