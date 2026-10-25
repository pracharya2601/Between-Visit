import { useEffect, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";

async function loadPracticeData() {
  const [practices, practitioners, clients] = await Promise.all(
    ["practices", "practitioners", "clients"].map((p) => axios.get(`${API}/${p}`).then((r) => r.data))
  );
  if (!practices.length) throw new Error("No practice");
  return { practice: practices[0], practitioner: practitioners[0], clients };
}

function PracticeView({ data }) {
  const { practice, practitioner, clients } = data;
  return (
    <div className="bv-stack">
      <section aria-labelledby="practice-heading">
        <p className="bv-eyebrow">Practice</p>
        <h1 id="practice-heading" className="bv-h1" data-testid="practice-name">{practice.name}</h1>
      </section>
      {practitioner && (
        <section aria-labelledby="practitioner-heading" className="bv-panel">
          <h2 id="practitioner-heading" className="bv-h2">Practitioner</h2>
          <p className="bv-strong" data-testid="practitioner-name">{practitioner.name}</p>
          <p data-testid="practitioner-role">{practitioner.role}</p>
        </section>
      )}
      <section aria-labelledby="clients-heading" className="bv-panel">
        <h2 id="clients-heading" className="bv-h2">Clients</h2>
        <ul className="bv-list" data-testid="client-list">
          {clients.map((c) => (
            <li key={c.id} className="bv-strong" data-testid={`client-name-${c.id}`}>{c.display_name}</li>
          ))}
        </ul>
      </section>
      <p>
        <Link to="/demo" className="bv-link" data-testid="try-the-demo-link">Try the demo</Link>
      </p>
    </div>
  );
}

export default function Home() {
  useTitle("Practice workspace");
  const [state, setState] = useState({ status: "loading", data: null });

  useEffect(() => {
    loadPracticeData()
      .then((data) => setState({ status: "ready", data }))
      .catch(() => setState({ status: "error", data: null }));
  }, []);

  return (
    <>
      <div aria-live="polite" role="status" className="bv-status" data-testid="status-region">
        {state.status === "loading" && <p data-testid="loading-message">Loading practice data…</p>}
        {state.status === "error" && <p className="bv-error" data-testid="error-message">Couldn't load practice data</p>}
      </div>
      {state.status === "ready" && <PracticeView data={state.data} />}
    </>
  );
}
