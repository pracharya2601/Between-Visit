import { useEffect } from "react";
import TimelineItem from "@/components/review/TimelineItem";

const FILTERS = [["all", "All"], ["spoken", "Spoken"], ["suppressed", "Suppressed"]];

export default function Timeline({ items, routine, filter, setFilter, selected, scrollToken, onSelect, onChanged }) {
  const shown = filter === "all" ? items : items.filter((i) => i.category === filter);
  useEffect(() => {
    if (!scrollToken || !selected) return;
    const el = document.getElementById(`timeline-item-${selected}`);
    if (el) { el.scrollIntoView({ block: "center" }); el.focus({ preventScroll: true }); }
  }, [scrollToken, selected]);

  return (
    <section aria-labelledby="timeline-heading" className="bv-review-list" data-testid="review-timeline">
      <h2 id="timeline-heading" className="bv-h2">Timeline</h2>
      <div className="bv-btn-row" role="group" aria-label="Show">
        {FILTERS.map(([key, label]) => (
          <button key={key} type="button" className="bv-btn bv-filter" aria-pressed={filter === key} onClick={() => setFilter(key)} data-testid={`timeline-filter-${key}`}>{label}</button>
        ))}
      </div>
      <p className="bv-tl-note" data-testid="timeline-routine-hidden">{routine} routine silences hidden</p>
      <p className="bv-tl-note" role="status" aria-live="polite" data-testid="timeline-count">{shown.length} items shown</p>
      <ol className="bv-tl" data-testid="timeline-list">
        {shown.map((i) => <TimelineItem key={i.id} item={i} selected={selected === i.id} onSelect={onSelect} onChanged={onChanged} />)}
      </ol>
    </section>
  );
}
