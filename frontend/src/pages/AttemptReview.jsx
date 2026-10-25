import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/lib/api";
import ReviewHeader from "@/components/review/ReviewHeader";
import Timeline from "@/components/review/Timeline";
import Path2D from "@/components/review/Path2D";
import PathLegend from "@/components/review/PathLegend";
import VersionHistory from "@/components/review/VersionHistory";

const Path3D = lazy(() => import("@/components/review/Path3D"));

function Unplaced({ entities }) {
  const list = entities.filter((e) => !e.pos);
  if (!list.length) return null;
  return <p className="bv-hint" data-testid="review-unplaced-entities">Known objects without a position (not drawn): {list.map((e) => `${e.label} (v${e.added_in})`).join(", ")}</p>;
}

function PathView({ id, path, dots, selected, onSelect }) {
  const entities = path.entities || [];
  if (path.mode === "none") return <><p className="bv-panel" data-testid="review-no-path">No path recorded for this attempt.</p><Unplaced entities={entities} /></>;
  return (
    <>
      {path.mode === "3d" ? (
        <Suspense fallback={<p>Loading the 3D view…</p>}><Path3D attemptId={id} api={API} path={path} dots={dots} entities={entities} selected={selected} onSelect={onSelect} /></Suspense>
      ) : (
        <Path2D path={path} dots={dots} entities={entities} selected={selected} onSelect={onSelect} />
      )}
      {path.mode === "3d" && path.aligned && <p className="bv-strong" data-testid="review-aligned-note">Run start aligned to the taught route's entrance.</p>}
      <PathLegend mode={path.mode} />
      <Unplaced entities={entities} />
    </>
  );
}

export default function AttemptReview() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [scrollToken, setScrollToken] = useState(0);
  const [historyToken, setHistoryToken] = useState(0);

  const load = useCallback(() => axios.get(`${API}/attempts/${id}/review`).then((r) => setData(r.data)).catch((ex) => {
    const code = ex.response?.status;
    setError(code === 404 ? "Attempt not found" : code === 409 ? "This attempt hasn't started yet." : "Couldn't load practice data");
  }), [id]);
  useEffect(() => { setData(null); setError(""); load(); }, [load]);
  const onCorrected = useCallback(() => { load(); setHistoryToken((n) => n + 1); }, [load]);

  const onSelect = useCallback((itemId, fromDot) => {
    setSelected(itemId);
    if (fromDot) { setFilter("all"); setScrollToken((n) => n + 1); }
  }, []);

  if (!data) {
    return (
      <div role="status" aria-live="polite" data-testid="review-status">
        {error ? <p className="bv-error" data-testid="attempt-review-error">{error}</p> : <p>Loading the review…</p>}
      </div>
    );
  }
  const dots = data.timeline.filter((i) => i.pos);
  return (
    <div className="bv-stack" data-testid="attempt-review-page">
      <ReviewHeader h={data.header} />
      <div className="bv-review">
        <section aria-labelledby="path-heading" className="bv-review-scene" data-testid="review-path">
          <h2 id="path-heading" className="bv-h2">Path</h2>
          <PathView id={id} path={data.path} dots={dots} selected={selected} onSelect={onSelect} />
        </section>
        <Timeline items={data.timeline} routine={data.header.routine_hidden} filter={filter} setFilter={setFilter} selected={selected} scrollToken={scrollToken} onSelect={onSelect} onChanged={onCorrected} />
      </div>
      <VersionHistory routeId={data.header.route_id} refreshToken={historyToken} onChanged={load} />
    </div>
  );
}
