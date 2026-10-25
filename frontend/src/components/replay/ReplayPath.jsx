const W = 420, H = 300, PAD = 30;

function bounds(pts) {
  const xs = pts.map((p) => p[0]), zs = pts.map((p) => p[1]);
  const [x0, x1, z0, z1] = [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)];
  const k = Math.min((W - 2 * PAD) / Math.max(x1 - x0, 1), (H - 2 * PAD) / Math.max(z1 - z0, 1));
  const ox = (W - (x1 - x0) * k) / 2, oz = (H - (z1 - z0) * k) / 2;
  return (p) => [ox + (p[0] - x0) * k, oz + (p[1] - z0) * k];
}

export default function ReplayPath({ s }) {
  const cps = s.checkpoints.filter((c) => c.position).map((c) => ({ ...c, p: [c.position.x, c.position.z] }));
  const ents = s.entities.filter((e) => e.position).map((e) => ({ ...e, p: [e.position.x, e.position.z] }));
  const all = [...s.path, ...cps.map((c) => c.p), ...ents.map((e) => e.p)];
  if (!all.length) return <p className="bv-row-meta" data-testid="replay-path-empty">No position data in this recording.</p>;
  const map = bounds(all);
  const line = s.path.map((p) => map(p).join(",")).join(" ");
  const here = s.path.length ? map(s.path[s.path.length - 1]) : null;
  const unplaced = s.entities.filter((e) => !e.position);
  return (
    <figure className="bv-replay-path" data-testid="replay-path">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Top-down path: ${s.path.length} positions, ${cps.length} checkpoints`}>
        {cps.length > 1 && <polyline points={cps.map((c) => map(c.p).join(",")).join(" ")} className="bv-rp-route" />}
        <polyline points={line} className="bv-rp-walked" data-testid="replay-path-line" />
        {cps.map((c) => { const [x, y] = map(c.p); return (
          <g key={c.order} data-testid={`replay-path-checkpoint-${c.order}`}>
            <rect x={x - 7} y={y - 7} width="14" height="14" className={c.name === s.last_checkpoint ? "bv-rp-cp bv-rp-cp-on" : "bv-rp-cp"} />
            <text x={x + 11} y={y + 5} className="bv-rp-text">{c.name}</text>
          </g>); })}
        {ents.map((e, i) => { const [x, y] = map(e.p); return <circle key={i} cx={x} cy={y} r="7" className="bv-rp-ent" />; })}
        {here && <circle cx={here[0]} cy={here[1]} r="9" className="bv-rp-here" data-testid="replay-path-here" />}
      </svg>
      <figcaption className="bv-row-meta">
        Line: walked so far · squares: checkpoints · dot: now
        {unplaced.length > 0 && <> · known (no position): {unplaced.map((e) => e.label).join(", ")}</>}
      </figcaption>
    </figure>
  );
}
