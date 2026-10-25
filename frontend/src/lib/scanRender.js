import * as THREE from "three";

const EYE = 1.6;

export function cameraFor(cps, i) {
  const p = cps[i].position;
  const next = cps[i + 1]?.position;
  const prev = cps[i - 1]?.position;
  const dir = next ? [next[0] - p[0], next[2] - p[2]] : prev ? [p[0] - prev[0], p[2] - prev[2]] : [0, -1];
  const len = Math.hypot(dir[0], dir[1]) || 1;
  return { eye: [p[0], EYE, p[2]], target: [p[0] + dir[0] / len, EYE - 0.15, p[2] + dir[1] / len] };
}

export async function renderViews(pointsUrl, colorsUrl, cps) {
  const pos = new Float32Array(await (await fetch(pointsUrl)).arrayBuffer());
  const cr = colorsUrl ? await fetch(colorsUrl) : null;
  const rgb = cr && cr.ok ? new Uint8Array(await cr.arrayBuffer()) : null;
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const col = new Float32Array(pos.length);
  for (let i = 0; i < pos.length; i += 3) {
    if (rgb && rgb.length === pos.length) { col[i] = rgb[i] / 255; col[i + 1] = rgb[i + 1] / 255; col[i + 2] = rgb[i + 2] / 255; }
    else { const c = new THREE.Color().setHSL(0.66 * (1 - Math.min(1, Math.max(0, pos[i + 1] / 3))), 0.6, 0.55); col[i] = c.r; col[i + 1] = c.g; col[i + 2] = c.b; }
  }
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#e8e6e1");
  scene.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 0.035, vertexColors: true, sizeAttenuation: true })));
  const canvas = document.createElement("canvas");
  canvas.width = 1024; canvas.height = 768;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(1024, 768, false);
  const cam = new THREE.PerspectiveCamera(70, 1024 / 768, 0.05, 200);
  const out = [];
  for (let i = 0; i < cps.length; i++) {
    const { eye, target } = cameraFor(cps, i);
    cam.position.set(...eye);
    cam.lookAt(...target);
    renderer.render(scene, cam);
    const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.9));
    out.push(new File([blob], `checkpoint-${i + 1}-render.jpg`, { type: "image/jpeg" }));
  }
  renderer.dispose(); g.dispose();
  return out;
}
