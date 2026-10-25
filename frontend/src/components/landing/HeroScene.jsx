import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import Scene3D from "@/components/teach/Scene3D";
import { API } from "@/lib/api";

const YELLOW = "#f5c400", GREEN = "#2fbf5f", AMBER = "#f0a020", WALKER = "#f5f2ea";
const PAUSE_MS = 2200;
const CHAIR_FRAME = 3;

function at(poses, ms) {
  let i = 0;
  while (i < poses.length - 1 && poses[i + 1][3] <= ms) i++;
  const a = poses[i], b = poses[Math.min(i + 1, poses.length - 1)];
  const k = b[3] > a[3] ? Math.min(1, (ms - a[3]) / (b[3] - a[3])) : 0;
  const dh = ((b[2] - a[2] + 540) % 360) - 180;
  return { i, x: a[0] + (b[0] - a[0]) * k, z: a[1] + (b[1] - a[1]) * k, h: a[2] + dh * k };
}

function Loop({ data, onPass }) {
  const marker = useRef();
  const poses = data.poses;
  const length = poses[poses.length - 1][3] + PAUSE_MS;
  const [state, setState] = useState({ pass: 0, i: 0 });
  const start = useRef(null);
  useFrame(({ clock }) => {
    if (start.current === null) start.current = clock.elapsedTime;
    const ms = (clock.elapsedTime - start.current) * 1000;
    const pass = Math.floor(ms / length) % 2;
    const p = at(poses, ms % length);
    if (marker.current) {
      marker.current.position.set(p.x, 0.05, p.z);
      marker.current.rotation.y = -THREE.MathUtils.degToRad(p.h);
    }
    if (p.i !== state.i || pass !== state.pass) setState({ pass, i: p.i });
  });
  const shown = state.i >= CHAIR_FRAME;
  useEffect(() => onPass(shown, state.pass), [shown, state.pass, onPass]);
  const trail = useMemo(() => poses.slice(0, state.i + 1).map((p) => [p[0], 0.05, p[1]]), [poses, state.i]);
  const sight = poses[CHAIR_FRAME];
  const cps = useMemo(() => (data.scene.checkpoints || []).filter((c) => c.position).map((c) => {
    const k = poses.findIndex((p) => Math.hypot(p[0] - c.position[0], p[1] - c.position[2]) < 1.5);
    return { ...c, at: k < 0 ? poses.length - 1 : k };
  }), [data.scene.checkpoints, poses]);
  const route = useMemo(() => (data.scene.trail || []).map((p) => [p[0], 0.04, p[2]]), [data.scene.trail]);
  return (
    <>
      {route.length > 1 && <Line points={route} color={YELLOW} lineWidth={2} transparent opacity={0.45} />}
      {trail.length > 1 && <Line points={trail} color={YELLOW} lineWidth={6} />}
      {cps.map((c) => (
        <mesh key={c.id} position={[c.position[0], 0.25, c.position[2]]} userData={{ reached: state.i >= c.at }}>
          <sphereGeometry args={[0.34, 20, 20]} />
          <meshBasicMaterial color={YELLOW} wireframe={state.i < c.at} />
        </mesh>
      ))}
      {shown && (
        <mesh position={[sight[0], 0.3, sight[1]]}>
          {state.pass === 0 ? <sphereGeometry args={[0.2, 16, 16]} /> : <boxGeometry args={[0.3, 0.3, 0.3]} />}
          <meshBasicMaterial color={state.pass === 0 ? GREEN : AMBER} />
        </mesh>
      )}
      {state.pass === 1 && data.chair && (
        <mesh position={[data.chair.pos[0], 1.3, data.chair.pos[1]]} rotation={[Math.PI, 0, 0]}><coneGeometry args={[0.3, 0.5, 3]} /><meshBasicMaterial color={AMBER} /></mesh>
      )}
      <group ref={marker}>
        <mesh position={[0, 0.15, 0]}><cylinderGeometry args={[0.22, 0.22, 0.3, 24]} /><meshBasicMaterial color={WALKER} /></mesh>
        <mesh position={[0, 0.15, -0.45]} rotation={[-Math.PI / 2, 0, 0]}><coneGeometry args={[0.14, 0.4, 16]} /><meshBasicMaterial color={WALKER} /></mesh>
      </group>
    </>
  );
}

export default function HeroScene({ label, onCard, onFail }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch(`${API}/demo/scene`).then((r) => (r.ok ? r.json() : Promise.reject())).then(setData).catch(onFail);
  }, [onFail]);
  if (!data) return null;
  return (
    <Scene3D scene={{ ...data.scene, trail: [] }} reached={[]} pointsUrl={`${API}/demo/points`} colorsUrl={data.scene.rgb ? `${API}/demo/points?colors=true` : null} label={label}
      testId="hero-scene" controls="none" hint="" view={{ position: [-2.6, 11.0, 3.2], target: [2.8, 0, -4.8] }}>
      <Loop data={data} onPass={onCard} />
    </Scene3D>
  );
}
