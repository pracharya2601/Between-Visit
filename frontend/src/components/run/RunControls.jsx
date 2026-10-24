export default function RunControls({ status, busy, onStart, onToggle, onRepeat, onHelp, onEnd }) {
  const ended = status === "ended";
  const active = status === "running" || status === "paused";
  const btn = "bv-btn bv-run-btn";
  return (
    <section className="bv-run-section" aria-label="Run controls" data-testid="run-controls">
      <button type="button" className={`${btn} bv-run-start`} disabled={busy || status !== "not_started"} onClick={onStart} data-testid="run-start-button">Start</button>
      <button type="button" className={btn} disabled={busy || !active} onClick={onToggle} data-testid="run-pause-resume-button">
        {status === "paused" ? "Resume" : "Pause"}
      </button>
      <button type="button" className={btn} disabled={busy || !active} onClick={onRepeat} data-testid="run-repeat-button">Repeat cue</button>
      <button type="button" className={`${btn} bv-run-help`} disabled={ended} onClick={onHelp} data-testid="run-help-button">Request help</button>
      <button type="button" className={`${btn} bv-run-end`} disabled={busy || !active} onClick={onEnd} data-testid="run-end-button">End</button>
    </section>
  );
}
