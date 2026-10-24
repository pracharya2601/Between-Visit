import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import OneTimeConfirmation, { runPath } from "@/components/OneTimeConfirmation";

const STATUS = { not_started: "Not started" };
const CUE = { minimal: "Minimal", standard: "Standard" };

function ExerciseItem({ ex, n }) {
  const [attempts, setAttempts] = useState(ex.attempts);
  const [created, setCreated] = useState(null);
  const [msg, setMsg] = useState("");
  const p = `exercise-${n}`;

  const onNew = async () => {
    setMsg("Creating attempt…");
    try {
      const r = await axios.post(`${API}/exercises/${ex.id}/attempts`);
      setAttempts((a) => [...a, r.data.attempt]);
      setCreated(r.data);
      setMsg("");
    } catch {
      setMsg("Couldn't create a new attempt. Try again.");
    }
  };

  return (
    <li className="bv-cp" data-testid={p}>
      <h3 className="bv-strong bv-ex-goal" data-testid={`${p}-goal`}>{ex.goal}</h3>
      <p className="bv-row-meta" data-testid={`${p}-meta`}>{ex.route_name} · v{ex.route_version} · {CUE[ex.cue_style]}</p>
      <h4 className="bv-label bv-label-spaced">Attempts</h4>
      <ul className="bv-list" data-testid={`${p}-attempts`}>
        {attempts.map((a) => (
          <li key={a.id} data-testid={`attempt-${a.stream_id}`}>
            <span className="bv-mono">{a.stream_id}</span> · {STATUS[a.status] ?? a.status}
            <br />
            <Link to={runPath(a.id)} className="bv-link bv-mono" data-testid={`attempt-${a.stream_id}-run-link`}>{runPath(a.id)}</Link>
          </li>
        ))}
      </ul>
      {created ? (
        <OneTimeConfirmation title="New attempt created" created={created} onClose={() => setCreated(null)} />
      ) : (
        <button type="button" className="bv-btn bv-btn-spaced" onClick={onNew} data-testid={`${p}-new-attempt-button`}>New attempt</button>
      )}
      <p aria-live="polite" role="status" className="bv-cp-msg" data-testid={`${p}-status`}>{msg}</p>
    </li>
  );
}

export default function ExerciseList({ exercises }) {
  return (
    <section aria-labelledby="exercises-heading">
      <h2 id="exercises-heading" className="bv-h2">Exercises</h2>
      {exercises.length === 0 ? (
        <p data-testid="no-exercises">No exercises assigned yet</p>
      ) : (
        <ul className="bv-cp-list" data-testid="exercise-list">
          {exercises.map((ex, i) => <ExerciseItem key={ex.id} ex={ex} n={i + 1} />)}
        </ul>
      )}
    </section>
  );
}
