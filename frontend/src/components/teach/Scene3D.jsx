import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

const PLANE_STYLE = {
  floor: { color: "#8a8a8a", opacity: 0.55 },
  wall: { color: "#7fa7d9", opacity: 0.12 },
  door: { color: "#ff8c00", opacity: 0.85 },
};

function heightColours(pos) {
  let min = Infinity, max = -Infinity;
  for (let i = 1; i < pos.length; i += 3) { min = Math.min(min, pos[i]); max = Math.max(max, pos[i]); }
  const out = new Float32Array(pos.length);
  const c = new THREE.Color();
  for (let i = 0; i < pos.length; i += 3) {
    c.setHSL(0.66 * (1 - (pos[i + 1] - min) / (max - min || 1)), 0.9, 0.5);
    out[i] = c.r; out[i + 1] = c.g; out[i + 2] = c.b;
  }
  return out;
}

function PointCloud({ positions }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    g.setAttribute("color", new THREE.BufferAttribute(heightColours(positions), 3));
    return g;
  }, [positions]);
  return <points geometry={geometry}><pointsMaterial size={0.05} vertexColors /></points>;
}

function PlaneMesh({ plane }) {
  const { geometry, matrix } = useMemo(() => {
    if (plane.polygon?.length >= 3) {
      const g = new THREE.ShapeGeometry(new THREE.Shape(plane.polygon.map(([x, z]) => new THREE.Vector2(x, -z))));
      g.rotateX(-Math.PI / 2);
      return { geometry: g, matrix: new THREE.Matrix4().fromArray(plane.transform) };
    }
    const g = new THREE.PlaneGeometry(plane.extent[0], plane.extent[1]);
    if (plane.align === "horizontal") g.rotateX(-Math.PI / 2);
    const m = new THREE.Matrix4().compose(new THREE.Vector3(...plane.center), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, plane.rotation_y, 0)), new THREE.Vector3(1, 1, 1));
    return { geometry: g, matrix: m };
  }, [plane]);
  const style = PLANE_STYLE[plane.class] || { color: "#cccccc", opacity: 0.25 };
  return (
    <mesh geometry={geometry} matrix={matrix} matrixAutoUpdate={false}>
      <meshBasicMaterial color={style.color} transparent opacity={style.opacity} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  );
}

function MarkerLabel({ n }) {
  const texture = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = c.height = 64;
    const g = c.getContext("2d");
    g.fillStyle = "#ffffff"; g.fillRect(4, 4, 56, 56);
    g.lineWidth = 6; g.strokeStyle = "#0b0b0b"; g.strokeRect(4, 4, 56, 56);
    g.fillStyle = "#0b0b0b"; g.font = "bold 40px sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(String(n), 32, 34);
    return new THREE.CanvasTexture(c);
  }, [n]);
  return <sprite position={[0, 0.7, 0]} scale={[0.7, 0.7, 0.7]}><spriteMaterial map={texture} depthTest={false} /></sprite>;
}

export default function Scene3D({ scene, pointsUrl, label, interactive = false, testId = "teach-scene", overlay = null, children }) {
  const [positions, setPositions] = useState(null);
  useEffect(() => {
    fetch(pointsUrl).then((r) => r.arrayBuffer()).then((b) => setPositions(new Float32Array(b))).catch(() => setPositions(new Float32Array(0)));
  }, [pointsUrl]);

  const { target, camPos } = useMemo(() => {
    const t = scene.trail.length ? scene.trail : [[0, 0, 0]];
    const xs = t.map((p) => p[0]), zs = t.map((p) => p[2]);
    const c = [(Math.min(...xs) + Math.max(...xs)) / 2, 0, (Math.min(...zs) + Math.max(...zs)) / 2];
    const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...zs) - Math.min(...zs)) + 3;
    const k = window.innerWidth < 700 ? 1.9 : 1.15;
    return { target: c, camPos: [c[0] + span * 0.3, span * k, c[2] + span * k * 0.75] };
  }, [scene.trail]);
  const summary = `3D map of the walk: ${scene.points.toLocaleString()} points (${scene.points_sent.toLocaleString()} shown), ${scene.planes.length} planes, ${scene.metres_walked.toFixed(1)} metres walked, ${scene.checkpoints.length} checkpoints. The checkpoint list gives the same information.`;

  return (
    <div className="bv-scene" role={interactive ? "group" : "img"} aria-label={label || summary} data-testid={testId}>
      <Canvas camera={{ position: camPos, fov: 50 }} data-testid={`${testId === "teach-scene" ? "teach" : testId}-canvas`}>
        <ambientLight />
        {positions && <PointCloud positions={positions} />}
        {scene.planes.map((p) => <PlaneMesh key={p.id} plane={p} />)}
        {scene.trail.length > 1 && <Line points={scene.trail} color="#003a70" lineWidth={4} />}
        {scene.checkpoints.filter((c) => c.position).map((c) => (
          <group key={c.id} position={c.position}>
            <mesh><sphereGeometry args={[0.25, 16, 16]} /><meshBasicMaterial color="#004d1a" /></mesh>
            <MarkerLabel n={c.order} />
          </group>
        ))}
        {children}
        <OrbitControls target={target} makeDefault />
      </Canvas>
      {overlay}
      <p className="bv-hint" aria-hidden="true">Drag to orbit, pinch or scroll to zoom.</p>
    </div>
  );
}
