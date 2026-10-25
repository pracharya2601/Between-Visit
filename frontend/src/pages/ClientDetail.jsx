import { Link, useParams } from "react-router-dom";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import { useApi } from "@/hooks/useApi";
import ExerciseList from "@/components/ExerciseList";
import ClientNotes from "@/components/ClientNotes";

export default function ClientDetail() {
  useTitle("Client");
  const { id } = useParams();
  const { status, data, code } = useApi(`${API}/clients/${id}`);
  const exercises = useApi(`${API}/clients/${id}/exercises`, 5000);
  return (
    <div className="bv-stack">
      <p><Link to="/clients" className="bv-link" data-testid="back-to-clients-link">Back to clients</Link></p>
      <div aria-live="polite" role="status" data-testid="client-status">
        {status === "loading" && <p>Loading client…</p>}
        {status === "error" && (
          <p className="bv-error" data-testid="client-error">{code === 404 ? "Client not found" : "Couldn't load practice data"}</p>
        )}
      </div>
      {status === "ready" && (
        <>
          <section aria-labelledby="client-heading">
            <p className="bv-eyebrow">Client</p>
            <h1 id="client-heading" className="bv-h1" data-testid="client-display-name">{data.display_name}</h1>
          </section>
          <section aria-labelledby="notes-heading" className="bv-panel">
            <h2 id="notes-heading" className="bv-h2">Notes</h2>
            <p data-testid="client-notes">{data.notes || "No notes"}</p>
          </section>
          {exercises.status === "ready" && <ExerciseList exercises={exercises.data} />}
          {exercises.status === "error" && <p className="bv-error" role="status">Couldn't load exercises</p>}
          <ClientNotes clientId={id} />
        </>
      )}
    </div>
  );
}
