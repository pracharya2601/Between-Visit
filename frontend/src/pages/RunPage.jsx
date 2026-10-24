import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";

const MESSAGES = {
  missing: "This link is missing its key. Ask your practitioner for a new attempt.",
  invalid: "This link's key isn't valid.",
  notfound: "Run not found",
  error: "Couldn't load this run. Try again.",
};

const keyFromHash = () => new URLSearchParams(window.location.hash.slice(1)).get("key") || "";

export default function RunPage() {
  const { id } = useParams();
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let alive = true;
    const key = keyFromHash();
    (async () => {
      try {
        const info = (await axios.get(`${API}/run/${id}`)).data;
        if (!key) return alive && setState({ status: "missing" });
        const { valid } = (await axios.post(`${API}/run/${id}/verify`, { key })).data;
        alive && setState(valid ? { status: "ready", info, key } : { status: "invalid" });
      } catch (e) {
        alive && setState({ status: e.response?.status === 404 ? "notfound" : "error" });
      }
    })();
    return () => { alive = false; };
  }, [id]);

  const { status, info, key } = state;
  return (
    <div className="bv-stack bv-run">
      <section aria-labelledby="run-heading">
        <p className="bv-eyebrow">Your run</p>
        <h1 id="run-heading" className="bv-h1">Route exercise</h1>
      </section>
      <div aria-live="polite" role="status" data-testid="run-status">
        {status === "loading" && <p>Loading your run…</p>}
        {MESSAGES[status] && <p className="bv-error" data-testid="run-error">{MESSAGES[status]}</p>}
      </div>
      {status === "ready" && (
        <section className="bv-panel" aria-labelledby="run-details-heading" data-testid="run-details">
          <h2 id="run-details-heading" className="bv-h2">Your exercise</h2>
          <dl className="bv-dl bv-run-dl">
            <dt>Goal</dt><dd data-testid="run-goal">{info.goal}</dd>
            <dt>Stream ID</dt><dd className="bv-mono" data-testid="run-stream-id">{info.stream_id}</dd>
            <dt>Key</dt><dd className="bv-mono" data-testid="run-key">{key}</dd>
          </dl>
          <p className="bv-hint">Your practitioner will tell you when to start. This page is a placeholder for now.</p>
        </section>
      )}
    </div>
  );
}
