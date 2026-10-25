import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import { speak, unlockSpeech } from "@/lib/speech";
import ReplaySetup from "@/components/replay/ReplaySetup";
import ReplayPath from "@/components/replay/ReplayPath";

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
      } catch { /* keep polling */ }
      t = setTimeout(poll, 500);
    };
    poll();
    return () => { alive = false; clearTimeout(t); };
  }, [attemptId]);
  return s;
}

function Stage({ s, muted, setMuted, isPublic }) {
  const frameSrc = s.frame_url ? `${process.env.REACT_APP_BACKEND_URL}${s.frame_url}` : null;
  return (
    <div className="bv-replay" data-testid="replay-stage">
      <div className="bv-replay-left">
        <div className="bv-replay-frame" data-testid="replay-frame">
          {frameSrc ? <img src={frameSrc} alt={`Recorded camera frame ${s.frame_index + 1} of ${s.recording.frame_count}`} data-testid="replay-frame-image" /> : <p>Waiting for the first frame…</p>}
        </div>
      </div>
      <div className="bv-replay-right">
        <p className="bv-strong" data-testid="replay-version-line">{s.version_line}</p>
        {s.recording.kind === "synthetic" && <p className="bv-replay-label" data-testid="replay-synthetic-label">{s.recording.label}</p>}
        <p data-testid="replay-last-checkpoint">Last checkpoint: <span className="bv-strong">{s.last_checkpoint ?? "none yet"}</span></p>
        <p data-testid="replay-counts">Cues spoken: {s.cues_spoken} · held back: {s.cues_held_back}</p>
        <p className="bv-row-meta" data-testid="replay-progress">Frame {Math.max(s.frame_index + 1, 0)} of {s.recording.frame_count} · {s.status === "ended" ? "Replay finished" : "Replaying"}</p>
        <ReplayPath s={s} />
        <div className="bv-replay-actions">
          <label className="bv-choice">
            <input type="checkbox" checked={muted} onChange={(e) => setMuted(e.target.checked)} data-testid="replay-mute-toggle" />
            <span>Mute voice</span>
          </label>
          {s.review_path && <Link to={s.review_path} className="bv-link bv-strong" data-testid="replay-review-link">{isPublic ? "See the practitioner review of this replay" : "Open the review"}</Link>}
        </div>
      </div>
      <p className="bv-replay-caption" aria-live="assertive" role="status" data-testid="replay-caption">{s.caption?.text ?? " "}</p>
    </div>
  );
}

export default function ReplayScreen({ routeId, isPublic }) {
  const [attemptId, setAttemptId] = useState(null);
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
      {s && <Stage s={s} muted={muted} setMuted={setMuted} isPublic={isPublic} />}
    </div>
  );
}
