import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "@/lib/api";
import { useTitle } from "@/hooks/useTitle";
import { useApi } from "@/hooks/useApi";
import AssignForm from "@/components/AssignForm";
import OneTimeConfirmation from "@/components/OneTimeConfirmation";

export default function AssignExercise() {
  useTitle("Assign an exercise");
  const { id } = useParams();
  const navigate = useNavigate();
  const route = useApi(`${API}/routes/${id}`);
  const clients = useApi(`${API}/clients`);
  const [created, setCreated] = useState(null);

  if (route.status !== "ready" || clients.status !== "ready") {
    const failed = route.status === "error" || clients.status === "error";
    return (
      <div aria-live="polite" role="status" data-testid="assign-load-status">
        {failed ? <p className="bv-error">{route.code === 404 ? "Route not available" : "Couldn't load practice data"}</p> : <p>Loading…</p>}
      </div>
    );
  }
  const r = route.data;
  return (
    <div className="bv-stack">
      <p><Link to={`/routes/${id}`} className="bv-link" data-testid="back-to-route-link">Back to route</Link></p>
      <section aria-labelledby="assign-heading">
        <p className="bv-eyebrow">Assign exercise · {r.name} · v{r.current_version}</p>
        <h1 id="assign-heading" className="bv-h1">Assign exercise</h1>
      </section>
      {r.current_version < 1 ? (
        <p className="bv-error" data-testid="assign-not-saved">Save the route before assigning it.</p>
      ) : created ? (
        <OneTimeConfirmation
          title="Exercise assigned"
          created={created}
          onClose={() => { const c = created.exercise.client_id; setCreated(null); navigate(`/clients/${c}`); }}
        />
      ) : (
        <AssignForm routeId={id} clients={clients.data} onCreated={setCreated} />
      )}
    </div>
  );
}
