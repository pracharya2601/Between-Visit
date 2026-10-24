import CopyField from "@/components/CopyField";

export default function RunSummary({ info, ended }) {
  return (
    <>
      <section className="bv-panel bv-run-section" aria-labelledby="summary-heading" data-testid="run-summary">
        <h2 id="summary-heading" className="bv-h2">Your exercise</h2>
        <h3 className="bv-label">Goal</h3>
        <p data-testid="run-goal">{info.goal}</p>
        <h3 className="bv-label bv-label-spaced">Checkpoints, in order</h3>
        {info.checkpoints.length ? (
          <ol className="bv-run-cps" data-testid="run-checkpoints">
            {info.checkpoints.map((name, i) => <li key={i}>{name}</li>)}
          </ol>
        ) : <p data-testid="run-checkpoints">No checkpoints</p>}
        <h3 className="bv-label bv-label-spaced">If you feel unsure</h3>
        <p data-testid="run-stop-rule">{info.stop_rule}</p>
      </section>
      <section className="bv-panel bv-run-section" aria-labelledby="glasscam-heading" data-testid="run-glasscam">
        <h2 id="glasscam-heading" className="bv-h2">GlassCam connection</h2>
        <CopyField id="run-stream-id" label="Stream ID" value={info.stream_id} disabled={ended} />
        <CopyField id="run-key" label="Key" value={info.key} disabled={ended} />
      </section>
    </>
  );
}
