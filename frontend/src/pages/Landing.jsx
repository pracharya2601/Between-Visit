import { Link } from "react-router-dom";
import { useTitle } from "@/hooks/useTitle";
import HeroVisual from "@/components/landing/HeroVisual";
import SpecialistRows from "@/components/landing/SpecialistRows";
import teachImg from "@/assets/landing/teach-review.webp";
import runImg from "@/assets/landing/client-run.webp";
import reviewImg from "@/assets/landing/review-timeline.webp";

const CDC = "https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html";
const ACVREP = "https://www.acvrep.org/newsitem?id=97";
const STEPS = [
  { title: "Teach by walking", text: "Walk the route once with the phone. Between Visit proposes checkpoints and builds a 3D map you review before saving.", img: teachImg, w: 543, h: 564,
    alt: "Teach-walk review screen: a 3D map of an L-shaped corridor with numbered checkpoint markers 1, 2 and 3 along the walked line." },
  { title: "Client practises", text: "Between appointments your client walks the route with smart glasses or a phone and hears short cues in a large caption.", img: runImg, w: 430, h: 860,
    alt: "Client run screen on a phone: status Running and the latest cue in large text, 'Chair ahead, about 2 metres.', above Start, Pause and Repeat cue buttons." },
  { title: "Review and correct (memory v2)", text: "You see every cue that was spoken or held back, with the reason, and correct the route memory, which saves a new version.", img: reviewImg, w: 437, h: 900,
    alt: "Review timeline: a spoken cue 'On route.' and a not-spoken checkpoint cue with the reason 'Held back: another cue 1.5 s earlier'." },
];

function Hero() {
  return (
    <section className="bv-l-hero" aria-labelledby="landing-heading" data-testid="landing-hero">
      <div className="bv-l-inner bv-l-hero-grid">
        <div className="bv-l-hero-text">
          <h1 id="landing-heading" className="bv-l-h1" data-testid="landing-headline">Route practice between visits, reviewed by the specialist.</h1>
          <p className="bv-l-sub" data-testid="landing-subline">Teach a route once by walking it. Your client practises with smart glasses. You review every cue.</p>
          <div className="bv-l-actions">
            <Link to="/demo" className="bv-l-btn bv-l-btn-primary" data-testid="landing-try-demo-button">Try the demo</Link>
            <Link to="/workspace" className="bv-l-btn bv-l-btn-ghost" data-testid="landing-workspace-button">Open the practice workspace</Link>
          </div>
        </div>
        <HeroVisual />
      </div>
    </section>
  );
}

function Stats() {
  return (
    <section className="bv-l-stats" aria-labelledby="stats-heading" data-testid="landing-stats">
      <div className="bv-l-inner">
        <h2 id="stats-heading" className="bv-sr-only">The need, in numbers</h2>
        <div className="bv-l-stat-grid">
          <p className="bv-l-stat" data-testid="landing-stat-cdc"><span className="bv-l-big">7.1M</span><span>Americans with vision loss glasses can't correct</span>
            <a href={CDC} className="bv-l-src" data-testid="landing-cdc-link">CDC, 2024 estimates</a></p>
          <p className="bv-l-stat" data-testid="landing-stat-acvrep"><span className="bv-l-big">4,068</span><span>certified vision-rehab professionals in all of North America</span>
            <a href={ACVREP} className="bv-l-src" data-testid="landing-acvrep-link">ACVREP, Jan 2025</a></p>
        </div>
        <p className="bv-l-ratio" data-testid="landing-ratio">1,700+ people with uncorrectable vision loss in the US for every certified professional in North America</p>
        <Link to="/research" className="bv-l-link" data-testid="landing-research-link">See the research</Link>
      </div>
    </section>
  );
}

function Steps() {
  return (
    <section className="bv-l-section" aria-labelledby="steps-heading" data-testid="landing-how">
      <div className="bv-l-inner">
        <h2 id="steps-heading" className="bv-l-h2">How it works</h2>
        <ol className="bv-l-cards" data-testid="landing-steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className="bv-l-card" data-testid={`landing-step-${i + 1}`}>
              <div className="bv-l-shot"><img src={s.img} alt={s.alt} width={s.w} height={s.h} loading="lazy" decoding="async" /></div>
              <h3 className="bv-l-h3"><span className="bv-l-num" aria-hidden="true">{i + 1}</span>{s.title}</h3>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export default function Landing() {
  useTitle("Route practice between visits");
  return (
    <div className="bv-landing2" data-testid="landing-page">
      <Hero />
      <Stats />
      <Steps />
      <SpecialistRows />
      <section className="bv-l-close" aria-labelledby="close-heading" data-testid="landing-closing">
        <div className="bv-l-inner">
          <h2 id="close-heading" className="bv-l-h2">See one route, two versions, in 20 seconds</h2>
          <Link to="/demo" className="bv-l-btn bv-l-btn-primary" data-testid="landing-closing-demo-button">Try the demo</Link>
        </div>
      </section>
    </div>
  );
}
