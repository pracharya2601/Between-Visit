import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";

const Scene3D = lazy(() => import("@/components/teach/Scene3D"));

function Walker({ w }) {
  if (!w) return null;
  const rot = w.heading_deg == null ? 0 : -(w.heading_deg * Math.PI) / 180;
  return (
    <group position={[w.x, w.y - 1.4, w.z]} rotation={[0, rot, 0]}>
      <mesh position={[0, 0.15, 0]}><cylinderGeometry args={[0.22, 0.22, 0.3, 24]} /><meshBasicMaterial color="#00b3ff" /></mesh>
      <mesh position={[0, 0.15, -0.45]} rotation={[-Math.PI / 2, 0, 0]}><coneGeometry args={[0.14, 0.4, 16]} /><meshBasicMaterial color="#ffffff" /></mesh>
    </group>
  );
}

function usePoll(fn, ms) {
  useEffect(() => {
    let alive = true;
    const tick = () => alive && fn();
    tick();
    const t = setInterval(tick, ms);
    return () => { alive = false; clearInterval(t); };
  }, [fn, ms]);
}

export default function TeachLive3D({ sessionId }) {
  const [scene, setScene] = useState(null);
  const [pointsKey, setPointsKey] = useState(0);
  const [frame, setFrame] = useState(null);
  const url = useRef(null);
  const loadScene = useRef(() => fetch(`${API}/teach/${sessionId}/scene`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).then((d) => d && setScene(d)).catch(() => {})).current;
  const bumpPoints = useRef(() => setPointsKey((k) => k + 1)).current;
  const loadFrame = useRef(() => fetch(`${API}/teach/${sessionId}/live-frame`, { cache: "no-store" })
    .then((r) => (r.status === 200 ? r.blob() : null))
    .then((b) => {
      if (url.current) URL.revokeObjectURL(url.current);
      url.current = b ? URL.createObjectURL(b) : null;
      setFrame(url.current);
    }).catch(() => {})).current;
  usePoll(loadScene, 1000);
  usePoll(bumpPoints, 2000);
  usePoll(loadFrame, 1000);
  useEffect(() => () => url.current && URL.revokeObjectURL(url.current), []);

  return (
    <section className="bv-panel bv-teach-live3d" aria-labelledby="teach-live3d-heading" data-testid="teach-live-3d">
      <h2 id="teach-live3d-heading" className="bv-h2">Live map</h2>
      <div className="bv-teach-live3d-grid">
        <div>
          {scene ? (
            <Suspense fallback={<p>Loading the 3D view…</p>}>
              <Scene3D scene={scene} pointsUrl={`${API}/teach/${sessionId}/points?k=${pointsKey}`} interactive testId="teach-live-scene"
                label={`Live 3D map while walking: ${scene.points.toLocaleString()} points, ${scene.metres_walked.toFixed(1)} metres walked, ${scene.checkpoints.length} checkpoints proposed. The counters below give the same information.`}
                hint="Updates while you walk. Drag to orbit.">
                <Walker w={scene.walker} />
              </Scene3D>
            </Suspense>
          ) : <p>Waiting for the map…</p>}
        </div>
        <div className="bv-live-picture" data-testid="teach-live-picture">
          {frame ? <img src={frame} alt="Newest picture from the glasses (not stored)" data-testid="teach-live-picture-image" /> : <p>No live picture right now.</p>}
        </div>
      </div>
    </section>
  );
}
