const fmt = (s) => {
  const t = Math.max(0, Math.floor(s));
  const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), sec = t % 60;
  const mm = String(m).padStart(h ? 2 : 1, "0"), ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
};

function headingText({ heading, available }, status) {
  if (heading != null) return `${heading}°`;
  if (available === false) return "not available";
  return status === "not_started" ? "Starts when you press Start" : "waiting for the compass";
}

export default function RunMetrics({ elapsed, motion, status }) {
  return (
    <section className="bv-run-section" aria-label="Run progress" data-testid="run-metrics">
      <dl className="bv-dl bv-run-dl">
        <dt>Elapsed</dt><dd data-testid="run-elapsed">{fmt(elapsed)}</dd>
        <dt>Heading</dt><dd data-testid="run-heading">{headingText(motion, status)}</dd>
        <dt>Steps</dt><dd data-testid="run-steps">{motion.available === false ? "not available" : `about ${motion.steps} steps`}</dd>
      </dl>
    </section>
  );
}
