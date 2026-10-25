import { useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { Line } from "@react-three/drei";

const FLOOR = 0.02;

function Marker({ p, entrance, selected, onDown }) {
  return (
    <group position={[p.x, FLOOR, p.z]}>
      <mesh onPointerDown={onDown} position={[0, 0.25, 0]}>
        <cylinderGeometry args={[0.28, 0.28, 0.5, 20]} />
        <meshBasicMaterial color={entrance ? "#ffb000" : selected ? "#00c2a8" : "#ffffff"} />
      </mesh>
      <mesh position={[0, 0.6, 0]}><sphereGeometry args={[0.12, 12, 12]} /><meshBasicMaterial color="#0b0b0b" /></mesh>
    </group>
  );
}

function FacingArrow({ from, facing }) {
  if (!facing) return null;
  const len = Math.hypot(facing[0], facing[1]) || 1;
  const ux = facing[0] / len, uz = facing[1] / len;
  const tip = [from.x + ux * 1.4, FLOOR + 0.05, from.z + uz * 1.4];
  const l = [tip[0] - ux * 0.4 - uz * 0.25, tip[1], tip[2] - uz * 0.4 + ux * 0.25];
  const r = [tip[0] - ux * 0.4 + uz * 0.25, tip[1], tip[2] - uz * 0.4 - ux * 0.25];
  return <Line points={[[from.x, FLOOR + 0.05, from.z], tip, l, tip, r]} color="#ffb000" lineWidth={6} />;
}

export function PlacementLayer({ points, facing, selected, onPlaceEntrance, onFacing, onAdd, onMovePoint, onSelect, onDragEnd }) {
  const controls = useThree((s) => s.controls);
  const drag = useRef(null);
  useEffect(() => {
    const up = () => {
      if (!drag.current) return;
      drag.current = null;
      if (controls) controls.enabled = true;
      onDragEnd();
    };
    window.addEventListener("pointerup", up);
    return () => window.removeEventListener("pointerup", up);
  }, [controls, onDragEnd]);

  const start = (kind, i) => { drag.current = { kind, i }; if (controls) controls.enabled = false; };
  const onFloorDown = (e) => {
    if (points.length) return;
    e.stopPropagation();
    onPlaceEntrance(e.point.x, e.point.z);
    start("facing");
  };
  const onFloorMove = (e) => {
    const d = drag.current;
    if (!d) return;
    if (d.kind === "facing") {
      const p = points[0];
      if (p && Math.hypot(e.point.x - p.x, e.point.z - p.z) > 0.25) onFacing([e.point.x - p.x, e.point.z - p.z]);
    } else onMovePoint(d.i, e.point.x, e.point.z);
  };
  const onFloorClick = (e) => {
    if (!points.length || !facing || e.delta > 4) return;
    onAdd(e.point.x, e.point.z);
  };

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} onPointerDown={onFloorDown} onPointerMove={onFloorMove} onClick={onFloorClick}>
        <planeGeometry args={[400, 400]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>
      {points.length > 1 && <Line points={points.map((p) => [p.x, FLOOR + 0.03, p.z])} color="#00c2a8" lineWidth={4} />}
      {points[0] && <FacingArrow from={points[0]} facing={facing} />}
      {points.map((p, i) => (
        <Marker key={i} p={p} entrance={i === 0} selected={selected === i}
          onDown={(e) => { e.stopPropagation(); onSelect(i); start(i === 0 ? "facing" : "move", i); }} />
      ))}
    </group>
  );
}
