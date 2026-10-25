import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/lib/api";

export function useSimilarity(cps) {
  const [warnings, setWarnings] = useState({});
  const key = JSON.stringify(cps.map((c) => [c.id, c.order, c.landmark_text, c.photo_url]));
  useEffect(() => {
    const list = JSON.parse(key).map(([id, order, landmark_text, photo_url]) => ({ id, order, landmark_text: landmark_text || "", photo_url }));
    if (list.length < 2) { setWarnings({}); return undefined; }
    let alive = true;
    const t = setTimeout(() => {
      axios.post(`${API}/checkpoints/similarity`, { checkpoints: list })
        .then((r) => alive && setWarnings(r.data.warnings))
        .catch(() => {});
    }, 300);
    return () => { alive = false; clearTimeout(t); };
  }, [key]);
  return warnings;
}
