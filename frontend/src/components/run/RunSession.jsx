import { useCallback, useEffect, useRef, useState } from "react";
import { speak, speakSetting, unlockSpeech } from "@/lib/speech";
import { useMotion } from "@/hooks/useMotion";
import { useWakeLock } from "@/hooks/useWakeLock";
import RunControls from "@/components/run/RunControls";
import EndConfirm from "@/components/run/EndConfirm";
import RunMetrics from "@/components/run/RunMetrics";
import RunSummary from "@/components/run/RunSummary";
import PhoneCamera from "@/components/run/PhoneCamera";

const STATUS_TEXT = { not_started: "Not started", running: "Running", paused: "Paused", ended: "This run has ended", pending: "Test stream" };

function useAnnouncer() {
  const [text, setText] = useState("");
  const say = useCallback((t) => { setText(""); setTimeout(() => setText(t), 100); }, []);
  return [text, say];
}

function useTicker(active) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [active]);
}

export default function RunSession({ info, api }) {
  const [run, setRunRaw] = useState({ ...info.state, at: performance.now() });
  const [caption, setCaption] = useState(info.last_cue?.text ?? "");
  const [announcement, announce] = useAnnouncer();
  const [speakOn, setSpeakOn] = useState(speakSetting.get);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [busy, setBusy] = useState(false);
  const cursor = useRef(info.last_cue?.seq ?? 0);
  const lastCue = useRef(info.last_cue?.text ?? "");
  const speakRef = useRef(speakOn);
  speakRef.current = speakOn;
  const { status } = run;
  const ended = status === "ended";
  const motion = useMotion(status === "running");
  useWakeLock(status === "running");
  useTicker(status === "running");
  const setRun = useCallback((s) => setRunRaw({ ...s, at: performance.now() }), []);
  const elapsed = run.elapsed_seconds + (status === "running" ? (performance.now() - run.at) / 1000 : 0);

  const showCue = useCallback((c, live) => {
    lastCue.current = c.text;
    setCaption(c.text);
    if (live) return;
    const spoken = speakRef.current && speak(c.text);
    api.post(`/cues/${c.seq}/ack`, { spoken: !!spoken, reason: spoken ? null : "speak_off" }).catch(() => {});
  }, [api]);

  useEffect(() => {
    if (ended) return;
    let alive = true, inFlight = false;
    const t = setInterval(async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const { data } = await api.get("/cues", { params: { after: cursor.current } });
        if (!alive) return;
        setRun(data.state);
        const c = data.cues[data.cues.length - 1];
        if (c) { cursor.current = c.seq; showCue(c, data.state.glasses_live); }
      } catch { /* next poll retries */ } finally { inFlight = false; }
    }, 1000);
    return () => { alive = false; clearInterval(t); };
  }, [ended, api, setRun, showCue]);

  const transition = async (action, okMsg) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/${action}`);
      setRun(data);
      announce(okMsg);
    } catch (e) {
      announce(e.response?.data?.detail || "That didn't work. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const onStart = () => {
    motion.requestPermission();
    unlockSpeech();
    transition("start", info.record_demo ? "Run started. This run is recorded as a demo." : "Run started");
    if (info.record_demo && speakRef.current) speak("This run is recorded as a demo.");
  };
  const onRepeat = async () => {
    const text = lastCue.current;
    if (!text) return announce("No cue yet");
    setCaption("");
    setTimeout(() => setCaption(text), 150);
    try {
      const { data } = await api.post("/repeat");
      if (!data.resent_to_glasses && speakRef.current) speak(text);
    } catch {
      if (speakRef.current) speak(text);
    }
  };
  const onHelp = async () => {
    try {
      await api.post("/help");
      announce("Help requested. Your practitioner has been told.");
    } catch {
      announce("Help didn't send. Call your practitioner.");
    }
  };
  const onSpeak = (e) => { speakSetting.set(e.target.checked); setSpeakOn(e.target.checked); };
  const glassesQuiet = (run.seconds_since_glasses_frame ?? elapsed) >= 3;

  return (
    <div className="bv-run">
      <h1 id="run-heading" className="bv-h1">Route exercise</h1>
      <p className={`bv-run-status ${ended ? "bv-run-ended" : ""}`} data-testid="run-state">{STATUS_TEXT[status] ?? status}</p>
      <section className="bv-run-section" aria-labelledby="caption-label">
        <h2 id="caption-label" className="bv-label">Latest cue</h2>
        <div className="bv-caption" aria-live="assertive" aria-atomic="true" data-testid="run-caption">{caption || <span className="bv-hint">No cue yet</span>}</div>
      </section>
      <RunControls status={status} busy={busy} onStart={onStart} onRepeat={onRepeat} onHelp={onHelp}
        onToggle={() => (status === "paused" ? transition("resume", "Run resumed") : transition("pause", "Run paused"))}
        onEnd={() => setConfirmEnd(true)} />
      {confirmEnd && !ended && (
        <EndConfirm onCancel={() => setConfirmEnd(false)} onConfirm={() => { setConfirmEnd(false); transition("end", "This run has ended"); }} />
      )}
      <p role="status" aria-live="polite" className="bv-run-announce" data-testid="run-announcement">{announcement}</p>
      <RunMetrics elapsed={elapsed} motion={motion} status={status} />
      <PhoneCamera attemptId={info.attempt_id} streamKey={info.key} running={status === "running"} glassesQuiet={glassesQuiet} motionRef={motion.latest} announce={announce} />
      <label className="bv-choice bv-run-section">
        <input type="checkbox" checked={speakOn} onChange={onSpeak} disabled={ended} data-testid="speak-cues-toggle" />
        <span>Speak cues aloud</span>
      </label>
      <RunSummary info={info} ended={ended} />
    </div>
  );
}
