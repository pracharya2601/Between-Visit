import { Component, Suspense, lazy, useCallback, useEffect, useState } from "react";
import still from "@/assets/landing/hero-still.webp";

const CARDS = ["Spoken: Chair ahead, about 2 metres.", "Held back: Known, chair confirmed in v2"];

const HeroScene = lazy(() => import("@/components/landing/HeroScene"));
const LABEL = "Animated 3D model of the demo corridor: a marker walks from the entrance down the hallway, turns right to the reception desk, and passes a chair. On one pass the chair cue is spoken; on the next it is held back because the chair was confirmed in route memory v2.";

function webglOk() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch {
    return false;
  }
}

class Boundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onFail(); }
  render() { return this.state.failed ? null : this.props.children; }
}

function Still() {
  return <img src={still} alt={LABEL} className="bv-hero-still" width="1200" height="800" data-testid="hero-still" />;
}

export default function HeroVisual() {
  const [mode, setMode] = useState("still");
  const [card, setCard] = useState(CARDS[1]);
  const [pass, setPass] = useState(1);
  const fail = useCallback(() => { setMode("still"); setCard(CARDS[1]); setPass(1); }, []);
  const onCard = useCallback((shown, p) => { setCard(CARDS[p]); setPass(p); }, []);
  useEffect(() => {
    if (mode !== "still") return;
    const t = setInterval(() => setPass((p) => { const n = 1 - p; setCard(CARDS[n]); return n; }), 6000);
    return () => clearInterval(t);
  }, [mode]);
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !webglOk()) return;
    const id = (window.requestIdleCallback || ((f) => setTimeout(f, 200)))(() => { setMode("3d"); setCard(CARDS[0]); setPass(0); });
    return () => (window.cancelIdleCallback || clearTimeout)(id);
  }, []);
  return (
    <div className={`bv-hero-visual bv-hero-${mode}`} data-testid="hero-visual" data-mode={mode}>
      {mode === "3d" && <img src={still} alt="" aria-hidden="true" className="bv-hero-still bv-hero-underlay" width="1200" height="800" />}
      {mode === "3d" ? (
        <Boundary onFail={fail}>
          <Suspense fallback={null}>
            <HeroScene label={LABEL} onCard={onCard} onFail={fail} />
          </Suspense>
        </Boundary>
      ) : <Still />}
      {card && (
        <div className={`bv-hero-card ${pass === 0 ? "bv-hero-card-spoken" : "bv-hero-card-held"}`} aria-hidden="true" data-testid="hero-caption-card">{card}</div>
      )}
    </div>
  );
}
