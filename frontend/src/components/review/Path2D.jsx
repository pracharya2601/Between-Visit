import { dotLabel } from "@/lib/format";

const W = 600;

function bounds(pts) {
  const xs = pts.map((p) => p[0]), zs = pts.map((p) => p[1]);
  const minX = Math.min(...xs) - 1.5, maxX = Math.max(...xs) + 1.5, minZ = Math.min(...zs) - 1.5, maxZ = Math.max(...zs) + 1.5;
  const k = W / Math.max(maxX - minX, maxZ - minZ, 4);
  return { k, minX, minZ, h: Math.max(240, (maxZ - minZ) * k) };
}

function Dot({ item, x, y, selected, onSelect }) {
  const r = selected ? 13 : 9;
  const act = () => onSelect(item.id, true);
  const shape = item.category === "spoken"
    ? <circle cx={x} cy={y} r={r} className="bv-dot-svg-spoken" />
    : <rect x={x - r} y={y - r} width={2 * r} height={2 * r} className="bv-dot-svg-suppressed" />;
  return (
    <g role="button" tabIndex={0} aria-label={dotLabel(item)} aria-pressed={selected} className={`bv-dot-svg${selected ? " bv-dot-svg-selected" : ""}`}
      onClick={act} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); act(); } }} data-testid={`path-dot-${item.id}`}>
      {shape}
    </g>
  );
}

export default function Path2D({ path, dots, entities = [], selected, onSelect }) {
  const placed = entities.filter((e) => e.pos);
  const all = [...path.trail, ...dots.map((d) => d.pos), ...placed.map((e) => e.pos)];
  const { k, minX, minZ, h } = bounds(all);
  const sx = (x) => (x - minX) * k, sy = (z) => (z - minZ) * k;
  const source = path.source === "steps" ? "estimated from heading and steps (about 0.7 m per step)" : "from the phone's AR tracking";
  return (
    <figure className="bv-path2d" data-testid="review-path-2d">
      <svg viewBox={`0 0 ${W} ${h}`} role="group" aria-label={`Top-down path ${source}, north up, with ${dots.length} cue dots`}>
        <polyline points={path.trail.map((p) => `${sx(p[0])},${sy(p[1])}`).join(" ")} className="bv-path-line" />
        {path.trail.length > 0 && <rect x={sx(path.trail[0][0]) - 8} y={sy(path.trail[0][1]) - 8} width={16} height={16} className="bv-path-start" transform={`rotate(45 ${sx(path.trail[0][0])} ${sy(path.trail[0][1])})`} />}
        {placed.map((e) => (
          <g key={e.id} role="img" aria-label={`Known object: ${e.label}, ${e.side}, from v${e.added_in}`} data-testid={`path-known-${e.id}`}>
            <polygon points={`${sx(e.pos[0])},${sy(e.pos[1]) - 14} ${sx(e.pos[0]) - 12},${sy(e.pos[1]) + 9} ${sx(e.pos[0]) + 12},${sy(e.pos[1]) + 9}`} className="bv-known-svg" />
            <text x={sx(e.pos[0]) + 16} y={sy(e.pos[1]) + 6} className="bv-known-text">{e.label}</text>
          </g>
        ))}
        {dots.map((d) => <Dot key={d.id} item={d} x={sx(d.pos[0])} y={sy(d.pos[1])} selected={selected === d.id} onSelect={onSelect} />)}
      </svg>
      <figcaption className="bv-hint">Top-down view, north up. Path {source}.</figcaption>
    </figure>
  );
}
