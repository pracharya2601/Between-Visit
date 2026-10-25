import { Component, Suspense, lazy, useCallback, useEffect, useState } from "react";
import still from "@/assets/landing/hero-still.webp";
import { API } from "@/lib/api";

const CARDS = ["Spoken: Chair ahead, about 2 metres.", "Held back: Known, chair confirmed in v2"];

const HeroScene = lazy(() => import("@/components/landing/HeroScene"));
const LABEL = "Animated 3D scan of a room: a marker walks the approved route past numbered checkpoints; cues spoken or held back are shown in the card.";

function webglOk() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch {
    return false;
  }
}

function reviewCards(timeline) {
  const spoken = timeline.find((i) => i.category === "spoken" && i.kind === "checkpoint" && i.text);
  const held = timeline.find((i) => i.category === "suppressed" && i.text && i.reason);
  if (!spoken || !held) return null;
  const short = (t) => (t.match(/^Checkpoint \d+: [^.]*\./) || [t])[0];
  return [`Spoken: ${short(spoken.text)}`, `Held back: ${short(held.text)} Reason: ${held.reason.replace(/^Held back: /, "")}.`];
}

function useCards() {
  const [cards, setCards] = useState(CARDS);
  useEffect(() => {
    fetch(`${API}/demo/scene`).then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => (d.chair || !d.review_attempt_id ? null : fetch(`${API}/attempts/${d.review_attempt_id}/review`).then((r) => (r.ok ? r.json() : null))))
      .then((rv) => { const real = rv && reviewCards(rv.timeline || []); if (real) setCards(real); })
      .catch(() => {});
  }, []);
  return cards;
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
  const cards = useCards();
  const [mode, setMode] = useState("still");
  const [pass, setPass] = useState(1);
  const fail = useCallback(() => { setMode("still"); setPass(1); }, []);
  const onCard = useCallback((shown, p) => setPass(p), []);
  useEffect(() => {
    if (mode !== "still") return;
    const t = setInterval(() => setPass((p) => 1 - p), 6000);
    return () => clearInterval(t);
  }, [mode]);
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !webglOk()) return;
    const id = (window.requestIdleCallback || ((f) => setTimeout(f, 200)))(() => { setMode("3d"); setPass(0); });
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
      <div className={`bv-hero-card ${pass === 0 ? "bv-hero-card-spoken" : "bv-hero-card-held"}`} aria-hidden="true" data-testid="hero-caption-card">{cards[pass]}</div>
    </div>
  );
}
