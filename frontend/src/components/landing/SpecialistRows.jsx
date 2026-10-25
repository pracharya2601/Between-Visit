import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API } from "@/lib/api";
import { mss } from "@/lib/format";

function pick(timeline) {
  const chair = timeline.find((i) => i.category === "spoken" && i.entity?.label === "chair");
  const held = timeline.find((i) => i.category === "suppressed" && i.reason?.startsWith("Held back: another cue"))
    || timeline.find((i) => i.category === "suppressed" && i.reason);
  return [chair, held].filter(Boolean).sort((a, b) => a.at - b.at);
}

export default function SpecialistRows() {
  const [rows, setRows] = useState(null);
  const [id, setId] = useState(null);
  useEffect(() => {
    fetch(`${API}/demo/scene`).then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => d.review_attempt_id ? fetch(`${API}/attempts/${d.review_attempt_id}/review`).then((r) => (r.ok ? r.json() : Promise.reject())).then((rv) => { setId(d.review_attempt_id); setRows(pick(rv.timeline)); }) : Promise.reject())
      .catch(() => setRows([]));
  }, []);
  if (!rows || rows.length === 0) return null;
  return (
    <section className="bv-l-section" aria-labelledby="sees-heading" data-testid="landing-specialist">
      <div className="bv-l-inner">
        <h2 id="sees-heading" className="bv-l-h2">What the specialist learns</h2>
        <ol className="bv-l-rows">
          {rows.map((r) => (
            <li key={r.id} className={`bv-l-row bv-l-row-${r.category}`} data-testid={`landing-row-${r.category}`}>
              <span className="bv-l-row-time">{mss(r.at)}</span>
              <span className="bv-l-row-kind">{r.category === "spoken" ? "Spoken" : "Held back"}</span>
              <span className="bv-l-row-text">{r.category === "spoken" ? r.text : `Would have said: ${r.text}`}</span>
              {r.reason && r.category !== "spoken" && <span className="bv-l-row-reason">Reason: {r.reason}</span>}
            </li>
          ))}
          <li className="bv-l-row bv-l-row-confirm" data-testid="landing-row-confirm">
            <span className="bv-l-row-time" aria-hidden="true" />
            <span className="bv-l-row-kind">Confirmed</span>
            <span className="bv-l-row-text">Specialist confirms the chair; route memory saved as v2.</span>
          </li>
        </ol>
        <Link to={`/review/${id}`} className="bv-l-textlink" data-testid="landing-open-review-link">Open the full review</Link>
      </div>
    </section>
  );
}
