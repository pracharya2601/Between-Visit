import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import { speak, unlockSpeech } from "@/lib/speech";
import ReplaySetup from "@/components/replay/ReplaySetup";
import ReplayPath from "@/components/replay/ReplayPath";
import Replay3D, { Legend3D } from "@/components/replay/Replay3D";

function useReplay(attemptId, muted) {
  const [s, setS] = useState(null);
  const lastSeq = useRef(null);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;
  useEffect(() => {
    if (!attemptId) return;
    let alive = true, t;
    const poll = async () => {
      try {
        const r = await axios.get(`${API}/replays/${attemptId}`);
        if (!alive) return;
        const c = r.data.caption;
        if (c && c.seq !== lastSeq.current) {
          lastSeq.current = c.seq;
          if (!mutedRef.current) speak(c.text);
        }
        setS(r.data);
        if (r.data.status === "ended") return;
      } catch (e) {
        if (e.response?.status === 404) return alive && setS({ missing: true });
      }
      t = setTimeout(poll, 500);
    };
    poll();
    return () => { alive = false; clearTimeout(t); };
  }, [attemptId]);
  return s;
}

function Info({ s, muted, setMuted, isPublic, freeLook, setFreeLook }) {
  return (
    <>
      <p className="bv-strong" data-testid="replay-version-line">{s.version_line}</p>
      <p className="bv-replay-labels">
        {s.recording.kind === "synthetic" && <span className="bv-replay-label" data-testid="replay-synthetic-label">{s.recording.label}</span>}
        {s.recording.model_label && <span className="bv-replay-label" data-testid="replay-model-label">{s.recording.model_label}</span>}
      </p>
      <p data-testid="replay-last-checkpoint">Last checkpoint: <span className="bv-strong">{s.last_checkpoint ?? "none yet"}</span></p>
      <p data-testid="replay-counts">Cues spoken: {s.cues_spoken} · held back: {s.cues_held_back}</p>
      <p className="bv-row-meta" data-testid="replay-progress">Frame {Math.max(s.frame_index + 1, 0)} of {s.recording.frame_count} · {s.status === "ended" ? "Replay finished" : "Replaying"}</p>
      {s.three ? <Legend3D /> : <ReplayPath s={s} />}
      <div className="bv-replay-actions">
        <label className="bv-choice">
          <input type="checkbox" checked={muted} onChange={(e) => setMuted(e.target.checked)} data-testid="replay-mute-toggle" />
          <span>Mute voice</span>
        </label>
        {s.three && (
          <label className="bv-choice">
            <input type="checkbox" checked={freeLook} onChange={(e) => setFreeLook(e.target.checked)} data-testid="replay-free-look-toggle" />
            <span>Free look</span>
          </label>
        )}
        {s.review_path && <Link to={s.review_path} className="bv-link bv-strong" data-testid="replay-review-link">{isPublic ? "See the practitioner review of this replay" : "Open the review"}</Link>}
      </div>
    </>
  );
}

function Caption({ text }) {
  const t = text ?? " ";
  const i = t.indexOf(". ");
  return (
    <p className="bv-replay-caption" aria-live="assertive" role="status" data-testid="replay-caption">
      {i > 0 ? <>{t.slice(0, i + 1)}<span className="bv-replay-caption-rest">{t.slice(i + 2)}</span></> : t}
    </p>
  );
}

function summary(s) {
  const known = s.three.entities.map((e) => e.label).join(", ") || "none";
  return `Current checkpoint: ${s.last_checkpoint ?? "none yet"}. Cues so far: ${s.cues_spoken} spoken, ${s.cues_held_back} held back. Known objects: ${known}.`;
}

function Stage({ s, muted, setMuted, isPublic }) {
  const [freeLook, setFreeLook] = useState(false);
  const frameSrc = s.frame_url ? `${process.env.REACT_APP_BACKEND_URL}${s.frame_url}` : null;
  const frame = (
    <div className="bv-replay-frame" data-testid="replay-frame">
      {frameSrc ? <img src={frameSrc} alt={`Recorded camera frame ${s.frame_index + 1} of ${s.recording.frame_count}`} data-testid="replay-frame-image" /> : <p>Waiting for the first frame…</p>}
    </div>
  );
  const info = <Info s={s} muted={muted} setMuted={setMuted} isPublic={isPublic} freeLook={freeLook} setFreeLook={setFreeLook} />;
  if (s.three) {
    return (
      <div className="bv-replay bv-replay-3dmode" data-testid="replay-stage">
        <div className="bv-replay-main">
          <Replay3D three={s.three} pointsBase={`${API}/replays/${s.attempt_id}/points`} freeLook={freeLook} />
          <p className="bv-sr-only" data-testid="replay-3d-summary">{summary(s)}</p>
        </div>
        <div className="bv-replay-right">{frame}{info}</div>
        <Caption text={s.caption?.text} />
      </div>
    );
  }
  return (
    <div className="bv-replay" data-testid="replay-stage">
      <div className="bv-replay-left">{frame}</div>
      <div className="bv-replay-right">{info}</div>
      <Caption text={s.caption?.text} />
    </div>
  );
}

export default function ReplayScreen({ routeId, isPublic, attemptId: initialId = null }) {
  useTitle(initialId ? "Replay" : isPublic ? "Demo" : "Replay demo run");
  const [attemptId, setAttemptId] = useState(initialId);
  const [muted, setMuted] = useState(false);
  const s = useReplay(attemptId, muted);
  const start = useCallback(async (body) => {
    unlockSpeech();
    const url = isPublic ? `${API}/demo/replays` : `${API}/routes/${routeId}/replays`;
    const r = await axios.post(url, body);
    setAttemptId(r.data.attempt_id);
  }, [isPublic, routeId]);
  return (
    <div className="bv-replay-page" data-testid="replay-screen">
      <h1 className="bv-replay-title" data-testid="replay-title">Demo replay{s?.route_name ? `: ${s.route_name}` : ""}</h1>
      {!attemptId && <ReplaySetup routeId={routeId} isPublic={isPublic} onStart={start} />}
      {attemptId && !s && <p role="status" data-testid="replay-loading">Starting the replay…</p>}
      {s?.missing && <p className="bv-error" role="status" data-testid="replay-not-found">Replay not found. It may have been removed after 24 hours.</p>}
      {s && !s.missing && <Stage s={s} muted={muted} setMuted={setMuted} isPublic={isPublic} />}
    </div>
  );
}
