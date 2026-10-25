import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import Scene3D from "@/components/teach/Scene3D";

const AMBER = "#e08a00", GREY = "#8a8a8a", PURPLE = "#7b2fbf";

function useReducedMotion() {
  const q = "(prefers-reduced-motion: reduce)";
  const [on, setOn] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const m = window.matchMedia(q);
    const f = () => setOn(m.matches);
    m.addEventListener("change", f);
    return () => m.removeEventListener("change", f);
  }, []);
  return on;
}

function TextSprite({ text, y = 0.9 }) {
  const texture = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = 256; c.height = 64;
    const g = c.getContext("2d");
    g.fillStyle = "#ffffff"; g.fillRect(2, 2, 252, 60);
    g.lineWidth = 4; g.strokeStyle = PURPLE; g.strokeRect(2, 2, 252, 60);
    g.fillStyle = "#2b0a4a"; g.font = "bold 34px sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(text, 128, 34);
    return new THREE.CanvasTexture(c);
  }, [text]);
  return <sprite position={[0, y, 0]} scale={[1.2, 0.3, 1]}><spriteMaterial map={texture} depthTest={false} /></sprite>;
}

function Marker({ pos, heading }) {
  const rot = heading == null ? 0 : -THREE.MathUtils.degToRad(heading);
  return (
    <group position={pos} rotation={[0, rot, 0]}>
      <mesh position={[0, 0.15, 0]}><cylinderGeometry args={[0.22, 0.22, 0.3, 24]} /><meshBasicMaterial color="#00b3ff" /></mesh>
      <mesh position={[0, 0.15, -0.45]} rotation={[-Math.PI / 2, 0, 0]}><coneGeometry args={[0.14, 0.4, 16]} /><meshBasicMaterial color="#ffffff" /></mesh>
    </group>
  );
}

function CameraRig({ pos, heading }) {
  const { camera } = useThree();
  const look = useRef(new THREE.Vector3(...pos));
  const want = useMemo(() => new THREE.Vector3(), []);
  useFrame((_, dt) => {
    const h = THREE.MathUtils.degToRad(heading ?? 0);
    const fx = Math.sin(h), fz = -Math.cos(h);
    want.set(pos[0] - fx * 4.5, 3.4, pos[2] - fz * 4.5);
    const k = 1 - Math.exp(-dt * 2.2);
    camera.position.lerp(want, k);
    look.current.lerp(new THREE.Vector3(pos[0] + fx * 2, 0.6, pos[2] + fz * 2), k);
    camera.lookAt(look.current);
  });
  return null;
}

export default function Replay3D({ three, pointsBase, freeLook, reached = [], testId = "replay-scene", animate = true }) {
  const reduced = useReducedMotion();
  const trail = three.run_trail;
  const now = trail.length ? trail[trail.length - 1] : [0, three.floor_y, 0];
  const y = three.floor_y + 0.25;
  const spoken = three.dots.filter((d) => d.category === "spoken").length;
  const held = three.dots.length - spoken;
  const follow = animate && !reduced && !freeLook;
  const label = `3D view of the demo corridor with the replay's trail, checkpoints reached: ${reached.join(", ") || "none yet"}, ${spoken} spoken cue dots, ${held} held-back cue dots and ${three.entities.length} known objects.`;
  return (
    <div className="bv-replay-3d" data-testid={`${testId}-wrap`}>
      <Scene3D scene={three.scene} pointsUrl={`${pointsBase}`} colorsUrl={three.scene.rgb ? `${pointsBase}?colors=true` : null} label={label} interactive={freeLook} reached={reached}
        testId={testId} controls={freeLook || !animate ? "orbit" : "none"} orbitTarget={freeLook ? [now[0], 0, now[2]] : undefined}
        hint={freeLook || !animate ? "Drag to orbit, pinch or scroll to zoom." : reduced ? "Fixed overview (reduced motion)." : "Camera follows the walk. Turn on Free look to orbit."}>
        {trail.length > 1 && <Line points={trail} color="#d6007a" lineWidth={5} />}
        {three.dots.map((d) => (
          <mesh key={d.id} position={[d.pos[0], y, d.pos[1]]} data-testid={`replay-dot-${d.id}`}>
            {d.category === "spoken" ? <sphereGeometry args={[0.17, 16, 16]} /> : <boxGeometry args={[0.26, 0.26, 0.26]} />}
            <meshBasicMaterial color={d.category === "spoken" ? AMBER : GREY} />
          </mesh>
        ))}
        {three.entities.map((e) => (
          <group key={e.id} position={[e.pos[0], three.floor_y, e.pos[1]]}>
            <mesh position={[0, 1.25, 0]} rotation={[Math.PI, 0, 0]}><coneGeometry args={[0.25, 0.4, 3]} /><meshBasicMaterial color={PURPLE} /></mesh>
            <TextSprite text={e.label} y={1.75} />
          </group>
        ))}
        <Marker pos={now} heading={three.heading_deg} />
        {follow && <CameraRig pos={now} heading={three.heading_deg} />}
      </Scene3D>
    </div>
  );
}

export function Legend3D() {
  return (
    <ul className="bv-legend3d" aria-label="3D view legend" data-testid="replay-3d-legend">
      <li><span className="bv-lg bv-lg-spoken" aria-hidden="true" /> Spoken cue (circle)</li>
      <li><span className="bv-lg bv-lg-held" aria-hidden="true" /> Held back (square)</li>
      <li><span className="bv-lg bv-lg-known" aria-hidden="true" /> Known object (triangle)</li>
      <li><span className="bv-lg bv-lg-now" aria-hidden="true" /> Now, with heading arrow</li>
    </ul>
  );
}
