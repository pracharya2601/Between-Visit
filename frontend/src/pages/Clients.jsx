import { Link } from "react-router-dom";
import { API } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

export default function Clients() {
  const { status, data } = useApi(`${API}/clients`);
  return (
    <div className="bv-stack">
      <section aria-labelledby="clients-page-heading">
        <p className="bv-eyebrow">Workspace</p>
        <h1 id="clients-page-heading" className="bv-h1">Clients</h1>
      </section>
      <div aria-live="polite" role="status" data-testid="clients-status">
        {status === "loading" && <p>Loading clients…</p>}
        {status === "error" && <p className="bv-error">Couldn't load practice data</p>}
      </div>
      {status === "ready" && (
        <ul className="bv-rows" data-testid="clients-list">
          {data.map((c) => (
            <li key={c.id}>
              <Link to={`/clients/${c.id}`} className="bv-row-link" data-testid={`client-link-${c.id}`}>{c.display_name}</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
