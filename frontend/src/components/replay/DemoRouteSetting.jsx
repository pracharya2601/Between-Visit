import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

export default function DemoRouteSetting({ routeId }) {
  const [real, setReal] = useState(false);
  const [setting, setSetting] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    axios.get(`${API}/routes/${routeId}/recordings`).then((r) => setReal(r.data.some((x) => x.kind === "real"))).catch(() => setReal(false));
    axios.get(`${API}/demo/setting`).then((r) => setSetting(r.data)).catch(() => setSetting(null));
  }, [routeId]);
  const save = (route_id) => {
    setError("");
    axios.put(`${API}/demo/setting`, { route_id }).then((r) => setSetting(r.data)).catch((e) => setError(e.response?.data?.detail || "Couldn't change the website demo."));
  };
  if (!setting) return null;
  const isDemo = setting.active_route_id === routeId;
  return (
    <section className="bv-demo-setting" aria-label="Website demo" data-testid="demo-route-setting">
      <p data-testid="demo-route-status">{isDemo ? "This route is the website demo." : setting.using_synthetic ? "The website demo uses the synthetic route." : "Another route is the website demo."}</p>
      {real && !isDemo && <button type="button" className="bv-btn" onClick={() => save(routeId)} data-testid="use-as-website-demo-button">Use as website demo</button>}
      {!setting.using_synthetic && <button type="button" className="bv-btn" onClick={() => save(null)} data-testid="back-to-synthetic-demo-button">Back to the synthetic demo</button>}
      {error && <p role="alert" data-testid="demo-route-error">{error}</p>}
    </section>
  );
}
