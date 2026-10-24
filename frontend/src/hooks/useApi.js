import { useEffect, useState } from "react";
import axios from "axios";

export function useApi(url, intervalMs = 0) {
  const [state, setState] = useState({ status: "loading", data: null, code: null });
  useEffect(() => {
    let alive = true;
    setState({ status: "loading", data: null, code: null });
    const load = () => axios.get(url)
      .then((r) => alive && setState({ status: "ready", data: r.data, code: 200 }))
      .catch((e) => alive && setState((s) => (s.status === "ready" ? s : { status: "error", data: null, code: e.response?.status ?? null })));
    load();
    const t = intervalMs ? setInterval(load, intervalMs) : null;
    return () => { alive = false; clearInterval(t); };
  }, [url, intervalMs]);
  return state;
}
