import { mss } from "@/lib/format";

export default function ReviewHeader({ h }) {
  const date = new Date(h.started_at).toLocaleDateString([], { weekday: "short", year: "numeric", month: "short", day: "numeric" });
  return (
    <section aria-labelledby="attempt-review-heading" data-testid="attempt-review-header">
      <p className="bv-eyebrow">Attempt review · {h.stream_id}</p>
      <h1 id="attempt-review-heading" className="bv-h1" data-testid="review-client-name">{h.client}</h1>
      <p className="bv-strong bv-review-route" data-testid="review-route">{h.route} · v{h.version}</p>
      <dl className="bv-dl bv-review-stats">
        <dt>Date</dt><dd data-testid="review-date">{date}</dd>
        <dt>Elapsed (no pauses)</dt><dd data-testid="review-elapsed">{mss(h.elapsed_seconds)}</dd>
        <dt>Checkpoints</dt><dd data-testid="review-checkpoints">Checkpoints reached {h.checkpoints_reached} of {h.checkpoints_total}</dd>
        <dt>Help requests</dt><dd data-testid="review-help-count">{h.help_count}</dd>
        <dt>Cues</dt><dd data-testid="review-cue-counts">Cues spoken: {h.cues_spoken} · suppressed: {h.cues_suppressed}</dd>
      </dl>
    </section>
  );
}
