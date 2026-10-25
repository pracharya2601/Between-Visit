const r1 = (v) => Math.round(v * 10) / 10;
export const headingOf = (f) => (f ? Math.round((Math.atan2(f[0], -f[1]) * 180) / Math.PI + 360) % 360 : null);
export const facingOf = (deg) => [Math.sin((deg * Math.PI) / 180), -Math.cos((deg * Math.PI) / 180)];

function Row({ p, i, prev, selected, onEdit, onRemove, onSelect }) {
  const id = `placement-point-${i + 1}`;
  const dist = prev ? r1(Math.hypot(p.x - prev.x, p.z - prev.z)) : null;
  return (
    <li className={`bv-place-row ${selected ? "bv-place-row-selected" : ""}`} data-testid={id}>
      <p className="bv-place-title">
        <span data-testid={`${id}-order`}>{i + 1}.</span>{" "}
        <span data-testid={`${id}-distance`}>{dist == null ? "Start of the route" : `${dist} m from ${i === 1 ? "the Entrance" : `checkpoint ${i}`}`}</span>
      </p>
      <label className="bv-label" htmlFor={`${id}-name`}>Name</label>
      <input id={`${id}-name`} className="bv-input" value={p.name} onFocus={() => onSelect(i)} onChange={(e) => onEdit(i, { name: e.target.value })} data-testid={`${id}-name-input`} />
      <div className="bv-place-xy">
        {["x", "z"].map((k) => (
          <label key={k} className="bv-label" htmlFor={`${id}-${k}`}>{k === "x" ? "Across (m)" : "Along (m)"}
            <input id={`${id}-${k}`} type="number" step="0.1" className="bv-input" value={r1(p[k])} onFocus={() => onSelect(i)}
              onChange={(e) => e.target.value !== "" && onEdit(i, { [k]: Number(e.target.value) })} data-testid={`${id}-${k}-input`} />
          </label>
        ))}
      </div>
      {i > 0 && <button type="button" className="bv-btn bv-btn-danger" onClick={() => onRemove(i)} aria-label={`Remove checkpoint ${i + 1}`} data-testid={`${id}-remove-button`}>Remove</button>}
    </li>
  );
}

export function PlacementList({ points, facing, selected, onEdit, onRemove, onSelect, onFacingDeg, onAddAhead, onUndo, canUndo }) {
  return (
    <section aria-labelledby="placement-list-heading" className="bv-panel" data-testid="placement-list">
      <h2 id="placement-list-heading" className="bv-h2">Placed checkpoints ({points.length})</h2>
      {!points.length && <p data-testid="placement-empty">Click the floor in the 3D view to place the Entrance, then drag to show which way the client faces.</p>}
      {points.length > 0 && (
        <label className="bv-label" htmlFor="placement-facing">Entrance facing (degrees, 0 = up the screen at the start)
          <input id="placement-facing" type="number" step="5" className="bv-input" value={headingOf(facing) ?? ""} placeholder="Drag in the 3D view or type"
            onChange={(e) => e.target.value !== "" && onFacingDeg(Number(e.target.value))} data-testid="placement-facing-input" />
        </label>
      )}
      <ol className="bv-place-list">
        {points.map((p, i) => <Row key={i} p={p} i={i} prev={points[i - 1]} selected={selected === i} onEdit={onEdit} onRemove={onRemove} onSelect={onSelect} />)}
      </ol>
      <div className="bv-btn-row">
        <button type="button" className="bv-btn" onClick={onAddAhead} disabled={!points.length || !facing} data-testid="placement-add-ahead-button">Add checkpoint 2 m ahead</button>
        <button type="button" className="bv-btn" onClick={onUndo} disabled={!canUndo} data-testid="placement-undo-button">Undo</button>
      </div>
    </section>
  );
}
