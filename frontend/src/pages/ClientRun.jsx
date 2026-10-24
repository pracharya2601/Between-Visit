import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import RunSession from "@/components/run/RunSession";

const MESSAGES = {
  missing: "This link is missing its key. Ask your practitioner for a new attempt.",
  invalid: "This link's key isn't valid.",
  notfound: "Run not found",
  error: "Couldn't load this run. Try again.",
};

const keyFromHash = () => new URLSearchParams(window.location.hash.slice(1)).get("key") || "";

export default function ClientRun() {
  const { id } = useParams();
  const key = useMemo(keyFromHash, []);
  const api = useMemo(() => axios.create({ baseURL: `${API}/run/${id}`, headers: { "X-Stream-Key": key } }), [id, key]);
  const [state, setState] = useState({ status: key ? "loading" : "missing" });

  useEffect(() => {
    if (!key) return;
    let alive = true;
    api.get("")
      .then((r) => alive && setState({ status: "ready", info: { ...r.data, key } }))
      .catch((e) => {
        const code = e.response?.status;
        alive && setState({ status: code === 404 ? "notfound" : code === 401 ? "invalid" : "error" });
      });
    return () => { alive = false; };
  }, [api, key]);

  if (state.status === "ready") return <RunSession info={state.info} api={api} />;
  return (
    <div className="bv-run">
      <h1 className="bv-h1">Route exercise</h1>
      <div aria-live="polite" role="status" data-testid="run-status">
        {state.status === "loading" ? <p>Loading your run…</p> : <p className="bv-error" data-testid="run-error">{MESSAGES[state.status]}</p>}
      </div>
    </div>
  );
}
