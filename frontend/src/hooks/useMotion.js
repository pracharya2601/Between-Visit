import { useCallback, useEffect, useRef, useState } from "react";

const needsPermission = () => typeof window.DeviceMotionEvent?.requestPermission === "function";

export function useMotion(running) {
  const [heading, setHeading] = useState(null);
  const [steps, setSteps] = useState(0);
  const [available, setAvailable] = useState(null);
  const runningRef = useRef(running);
  runningRef.current = running;
  const attached = useRef(false);
  const latest = useRef({ heading: null, steps: 0 });

  const attach = useCallback(() => {
    if (attached.current) return;
    attached.current = true;
    let avg = 9.8, above = false, last = 0;
    const onOrient = (e) => {
      const h = typeof e.webkitCompassHeading === "number" ? e.webkitCompassHeading : e.alpha != null ? (360 - e.alpha) % 360 : null;
      if (h == null) return;
      latest.current.heading = Math.round(h);
      setHeading(latest.current.heading);
      setAvailable(true);
    };
    const onMotion = (e) => {
      const a = e.accelerationIncludingGravity;
      if (!a || a.x == null) return;
      setAvailable(true);
      const m = Math.hypot(a.x, a.y, a.z);
      avg = avg * 0.95 + m * 0.05;
      const now = performance.now();
      if (!above && m > avg + 1.5 && now - last > 300) {
        above = true;
        last = now;
        if (runningRef.current) setSteps((s) => (latest.current.steps = s + 1));
      } else if (above && m < avg) above = false;
    };
    window.addEventListener("deviceorientation", onOrient);
    window.addEventListener("devicemotion", onMotion);
    setTimeout(() => setAvailable((v) => v ?? false), 3000);
  }, []);

  // Call synchronously inside the Start tap: iOS only grants permission from a user gesture.
  const requestPermission = useCallback(() => {
    if (needsPermission()) {
      const o = typeof window.DeviceOrientationEvent?.requestPermission === "function" ? window.DeviceOrientationEvent.requestPermission() : Promise.resolve("granted");
      Promise.all([window.DeviceMotionEvent.requestPermission(), o])
        .then((r) => (r.includes("granted") ? attach() : setAvailable(false)))
        .catch(() => setAvailable(false));
    } else if (window.DeviceMotionEvent || window.DeviceOrientationEvent) attach();
    else setAvailable(false);
  }, [attach]);

  useEffect(() => {
    if (running && !needsPermission()) requestPermission();
  }, [running, requestPermission]);

  return { heading, steps, available, requestPermission, latest };
}
