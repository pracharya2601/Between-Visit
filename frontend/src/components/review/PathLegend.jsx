export default function PathLegend({ mode }) {
  return (
    <ul className="bv-legend" aria-label="Legend" data-testid="review-path-legend">
      <li><span className="bv-dot bv-dot-spoken bv-legend-swatch" aria-hidden="true" /> Spoken cue (green circle)</li>
      <li><span className="bv-dot bv-dot-suppressed bv-legend-swatch" aria-hidden="true" /> Suppressed cue (orange square)</li>
      <li><span className="bv-known-mark bv-legend-swatch" aria-hidden="true" /> Known object from route memory (purple triangle, labelled)</li>
      <li><span className={`bv-legend-line ${mode === "3d" ? "bv-legend-run" : "bv-legend-path"}`} aria-hidden="true" /> This run's path</li>
      {mode === "3d" && <li><span className="bv-legend-line bv-legend-taught" aria-hidden="true" /> Taught route</li>}
      {mode === "3d" && <li><span className="bv-marker" aria-hidden="true">1</span> Checkpoint</li>}
      {mode === "2d" && <li><span className="bv-legend-start" aria-hidden="true" /> Start</li>}
    </ul>
  );
}
