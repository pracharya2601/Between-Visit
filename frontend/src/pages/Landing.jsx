import { Link } from "react-router-dom";
import { useTitle } from "@/hooks/useTitle";
import HeroVisual from "@/components/landing/HeroVisual";
import SpecialistRows from "@/components/landing/SpecialistRows";
import teachImg from "@/assets/landing/teach-review.webp";
import runImg from "@/assets/landing/client-run.webp";
import reviewImg from "@/assets/landing/review-timeline.webp";

const CDC = "https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html";
const ACVREP = "https://www.acvrep.org/newsitem?id=97";
const HUMAN_PHOTO = null;
const STEPS = [
  { title: "Teach", text: "The specialist walks the route and approves the proposed checkpoints.", img: teachImg, w: 543, h: 452,
    alt: "A 3D scan of a room with numbered checkpoints 1 to 4 along the route." },
  { title: "Practise", text: "The client follows it with smart glasses or a phone. It stays quiet unless a cue helps.", img: runImg, w: 430, h: 860,
    alt: "Client run screen on a phone: status Running and the latest cue in large text, 'Chair ahead, about 2 metres.', above Start, Pause and Repeat cue buttons." },
  { title: "Review", text: "The specialist sees what was spoken, what was held back and why, and corrects the route memory.", img: reviewImg, w: 437, h: 900,
    alt: "Review timeline: a spoken cue 'On route.' and a not-spoken checkpoint cue with the reason 'Held back: another cue 1.5 s earlier'." },
];
const SAFEGUARDS = ["Specialist-approved indoor routes only", "Experimental practice tool", "A human reviews every AI observation",
  "Stops and asks for help when unsure", "Does not replace a cane, guide dog or O&M specialist", "Not a medical or safety device"];

export function RouteMotif({ nodes = 3, className = "" }) {
  const xs = Array.from({ length: nodes }, (_, i) => 12 + (i * 376) / Math.max(1, nodes - 1));
  return (
    <svg className={`bv-l-motif ${className}`} viewBox="0 0 400 24" aria-hidden="true" focusable="false">
      <line x1="12" y1="12" x2="388" y2="12" className="bv-l-motif-line" />
      {xs.map((x, i) => <circle key={i} cx={x} cy="12" r="7" className="bv-l-motif-node" style={{ animationDelay: `${0.6 + i * 0.35}s` }} />)}
    </svg>
  );
}

function Hero() {
  return (
    <section className="bv-l-hero" aria-labelledby="landing-heading" data-testid="landing-hero">
      <div className="bv-l-inner bv-l-hero-grid">
        <div className="bv-l-hero-text">
          <RouteMotif className="bv-l-motif-hero" />
          <h1 id="landing-heading" className="bv-l-h1" data-testid="landing-headline">Teach the route once. Review every decision.</h1>
          <p className="bv-l-sub" data-testid="landing-subline">Between Visit turns a walked route into specialist-approved spatial memory for practice between appointments.</p>
          <div className="bv-l-actions">
            <Link to="/demo" className="bv-l-btn bv-l-btn-primary" data-testid="landing-try-demo-button">Watch the 20-second demo</Link>
            <Link to="/workspace" className="bv-l-textlink bv-l-textlink-dark" data-testid="landing-workspace-button">Open the specialist workspace</Link>
          </div>
        </div>
        <HeroVisual />
      </div>
    </section>
  );
}

function Problem() {
  return (
    <section className="bv-l-paper bv-l-section" aria-labelledby="problem-heading" data-testid="landing-problem">
      <div className="bv-l-inner bv-l-split">
        <RouteMotif nodes={2} className="bv-l-motif-divider" />
        <h2 id="problem-heading" className="bv-l-h2">The gap between visits</h2>
        <p className="bv-l-statement">O&amp;M specialists teach a route in person, but clients practise alone between visits and the specialist cannot see how it went.</p>
      </div>
    </section>
  );
}

function DemoStrip() {
  return (
    <section className="bv-l-dark bv-l-section" aria-labelledby="demo-heading" data-testid="landing-demo-strip">
      <div className="bv-l-inner">
        <h2 id="demo-heading" className="bv-l-h2">One route, two versions</h2>
        <ol className="bv-l-versions">
          <li className="bv-l-version" data-testid="landing-version-v1">
            <p className="bv-l-version-tag">v1</p>
            <p className="bv-l-version-title">v1: chair announced</p>
            <p className="bv-l-chip bv-l-chip-spoken">Spoken: Chair ahead, about 2 metres.</p>
          </li>
          <li className="bv-l-version bv-l-version-v2" data-testid="landing-version-v2">
            <p className="bv-l-version-tag">v2</p>
            <p className="bv-l-version-title">v2: chair confirmed by specialist, held back</p>
            <p className="bv-l-chip bv-l-chip-held">Held back: Known, chair confirmed in v2</p>
          </li>
        </ol>
        <Link to="/demo" className="bv-l-textlink bv-l-textlink-dark" data-testid="landing-demo-strip-link">Watch both versions in the demo</Link>
      </div>
    </section>
  );
}

function Journey() {
  return (
    <section className="bv-l-paper bv-l-section" aria-labelledby="steps-heading" data-testid="landing-how">
      <div className="bv-l-inner">
        <h2 id="steps-heading" className="bv-l-h2">Teach → Practise → Review</h2>
        <ol className="bv-l-journey" data-testid="landing-steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className="bv-l-step" data-testid={`landing-step-${i + 1}`}>
              <span className="bv-l-step-node" aria-hidden="true">{i + 1}</span>
              <h3 className="bv-l-h3">{s.title}</h3>
              <p className="bv-l-step-text">{s.text}</p>
              <div className="bv-l-shot"><img src={s.img} alt={s.alt} width={s.w} height={s.h} loading="lazy" decoding="async" /></div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Human() {
  return (
    <section className={`bv-l-section ${HUMAN_PHOTO ? "bv-l-human-photo" : ""}`} aria-labelledby="human-heading" data-testid="landing-human">
      <div className="bv-l-inner bv-l-split">
        <RouteMotif nodes={2} className="bv-l-motif-divider" />
        <h2 id="human-heading" className="bv-l-h2">People decide. The tool stays quiet.</h2>
        <div>
          {HUMAN_PHOTO && <img src={HUMAN_PHOTO.src} alt={HUMAN_PHOTO.alt} className="bv-l-human-img" />}
          <p className="bv-l-body">The specialist decides the route and every checkpoint on it. The glasses are a quiet tool that speaks only when a cue helps. The client practises at their own pace, as often as they like, between appointments.</p>
        </div>
      </div>
    </section>
  );
}

function Research() {
  return (
    <section className="bv-l-paper bv-l-section" aria-labelledby="stats-heading" data-testid="landing-stats">
      <div className="bv-l-inner">
        <RouteMotif nodes={2} className="bv-l-motif-divider" />
        <h2 id="stats-heading" className="bv-l-h2">The research</h2>
        <div className="bv-l-stat-grid">
          <p className="bv-l-stat" data-testid="landing-stat-cdc"><span className="bv-l-big">7.1M</span><span>Americans with vision loss glasses can't correct</span>
            <a href={CDC} className="bv-l-src" data-testid="landing-cdc-link">CDC, 2024 estimates</a></p>
          <p className="bv-l-stat" data-testid="landing-stat-acvrep"><span className="bv-l-big">4,068</span><span>certified professionals across North America</span>
            <a href={ACVREP} className="bv-l-src" data-testid="landing-acvrep-link">ACVREP, Jan 2025</a></p>
        </div>
        <p className="bv-l-ratio" data-testid="landing-ratio">These figures cover different populations (US prevalence vs North American certifications), so they are not a precise caseload ratio, but they show how few certified professionals there are.</p>
        <Link to="/research" className="bv-l-textlink" data-testid="landing-research-link">See the research</Link>
      </div>
    </section>
  );
}

function Safeguards() {
  return (
    <section className="bv-l-section" aria-labelledby="safeguards-heading" data-testid="landing-safeguards">
      <div className="bv-l-inner bv-l-split">
        <RouteMotif nodes={2} className="bv-l-motif-divider" />
        <h2 id="safeguards-heading" className="bv-l-h2">Professional safeguards</h2>
        <ul className="bv-l-safeguards">
          {SAFEGUARDS.map((s, i) => <li key={s} data-testid={`landing-safeguard-${i + 1}`}>{s}</li>)}
        </ul>
      </div>
    </section>
  );
}

export default function Landing() {
  useTitle("Route practice between visits");
  return (
    <div className="bv-landing2" data-testid="landing-page">
      <Hero />
      <Problem />
      <DemoStrip />
      <Journey />
      <SpecialistRows />
      <Human />
      <Research />
      <Safeguards />
      <section className="bv-l-close" aria-labelledby="close-heading" data-testid="landing-closing">
        <div className="bv-l-inner">
          <RouteMotif nodes={4} className="bv-l-motif-close" />
          <h2 id="close-heading" className="bv-l-h2">See one route become measurable practice.</h2>
          <Link to="/demo" className="bv-l-btn bv-l-btn-primary" data-testid="landing-closing-demo-button">Try the 20-second demo</Link>
        </div>
      </section>
    </div>
  );
}
