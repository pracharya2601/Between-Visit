import { useEffect, useState } from "react";
import axios from "axios";

export function useApi(url) {
  const [state, setState] = useState({ status: "loading", data: null, code: null });
  useEffect(() => {
    let alive = true;
    setState({ status: "loading", data: null, code: null });
    axios.get(url)
      .then((r) => alive && setState({ status: "ready", data: r.data, code: 200 }))
      .catch((e) => alive && setState({ status: "error", data: null, code: e.response?.status ?? null }));
    return () => { alive = false; };
  }, [url]);
  return state;
}
