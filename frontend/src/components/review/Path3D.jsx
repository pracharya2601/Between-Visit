import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import Scene3D from "@/components/teach/Scene3D";
import { dotLabel } from "@/lib/format";

function Projector({ dots, y, refs }) {
  const { camera, size } = useThree();
  const v = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    for (const d of dots) {
      const el = refs.current[d.id];
      if (!el) continue;
      v.set(d.pos[0], y + 0.4, d.pos[1]).project(camera);
      el.style.transform = `translate(${((v.x + 1) / 2) * size.width}px, ${((1 - v.y) / 2) * size.height}px) translate(-50%, -50%)`;
      el.style.visibility = v.z > 1 ? "hidden" : "visible";
    }
  });
  return null;
}

export default function Path3D({ attemptId, api, path, dots, entities = [], selected, onSelect }) {
  const placed = entities.filter((e) => e.pos);
  const refs = useRef({});
  const label = `3D view of the taught route with this run's trail and ${dots.length} cue dots. The timeline gives the same information.`;
  const colorsUrl = path.scene.rgb ? `${api}/attempts/${attemptId}/review/colors` : null;
  const overlay = (
    <div className="bv-dot-layer">
      {dots.map((d) => (
        <button key={d.id} ref={(el) => { refs.current[d.id] = el; }} type="button" aria-label={dotLabel(d)} aria-pressed={selected === d.id}
          onClick={() => onSelect(d.id, true)} className={`bv-dot bv-dot-abs bv-dot-${d.category}${selected === d.id ? " bv-dot-selected" : ""}`} data-testid={`path-dot-${d.id}`} />
      ))}
      {placed.map((e) => (
        <span key={e.id} ref={(el) => { refs.current[`known-${e.id}`] = el; }} className="bv-known-3d" role="img" aria-label={`Known object: ${e.label}, ${e.side}, from v${e.added_in}`} data-testid={`path-known-${e.id}`}>
          <span className="bv-known-mark" aria-hidden="true" /> {e.label}
        </span>
      ))}
    </div>
  );
  return (
    <>
    {path.scene.model_label && <p className="bv-replay-label" data-testid="review-model-label">{path.scene.model_label}</p>}
    <Scene3D scene={path.scene} pointsUrl={`${api}/attempts/${attemptId}/review/points`} colorsUrl={colorsUrl} label={label} interactive testId="review-scene" overlay={overlay}>
      {path.run_trail.length > 1 && <Line points={path.run_trail} color="#d6007a" lineWidth={5} />}
      <Projector dots={[...dots, ...placed.map((e) => ({ id: `known-${e.id}`, pos: e.pos }))]} y={path.floor_y} refs={refs} />
    </Scene3D>
    </>
  );
}
