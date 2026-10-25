import { useState } from "react";
import { mss } from "@/lib/format";
import CorrectionControls from "@/components/review/CorrectionControls";

export default function TimelineItem({ item, selected, onSelect, onChanged }) {
  const [open, setOpen] = useState(false);
  const p = `timeline-item-${item.id}`;
  return (
    <li id={p} tabIndex={-1} className={`bv-tl-item bv-tl-${item.category}${selected ? " bv-tl-selected" : ""}`} data-testid={p} data-kind={item.kind} data-category={item.category}>
      <p className="bv-tl-head">
        <span className="bv-tl-time" data-testid={`${p}-time`}>{mss(item.at)}</span>
        <span className="bv-tl-kind">{item.label}</span>
      </p>
      <p className="bv-tl-text" data-testid={`${p}-text`}>{item.would_have_said ? `Would have said: ${item.text}` : item.text}</p>
      {item.reason && <p className="bv-tl-reason" data-testid={`${p}-reason`}>Reason: {item.reason}</p>}
      {item.entity && <CorrectionControls item={item} onChanged={onChanged} />}
      {(item.pos || item.raw) && (
        <div className="bv-btn-row">
          {item.pos && (
            <button type="button" className="bv-btn" aria-pressed={selected} onClick={() => onSelect(item.id, false)} data-testid={`${p}-show-button`}>Show on path</button>
          )}
          {item.raw && (
            <button type="button" className="bv-btn" aria-expanded={open} aria-controls={`${p}-details`} onClick={() => setOpen((o) => !o)} data-testid={`${p}-details-button`}>Details</button>
          )}
        </div>
      )}
      {open && <pre id={`${p}-details`} className="bv-tl-json" data-testid={`${p}-details`}>{JSON.stringify(item.raw, null, 2)}</pre>}
    </li>
  );
}
