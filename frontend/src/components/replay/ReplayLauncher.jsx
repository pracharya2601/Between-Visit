import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";

export default function ReplayLauncher({ routeId }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    axios.get(`${API}/routes/${routeId}/recordings`).then((r) => setCount(r.data.length)).catch(() => setCount(0));
  }, [routeId]);
  if (!count) return null;
  return (
    <p data-testid="replay-launcher">
      <Link to={`/routes/${routeId}/replay`} className="bv-btn" data-testid="replay-demo-run-link">Replay demo run</Link>
      <span className="bv-row-meta"> {count} recording{count > 1 ? "s" : ""}</span>
    </p>
  );
}
