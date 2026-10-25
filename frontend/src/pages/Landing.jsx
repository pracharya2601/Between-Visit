import { Link } from "react-router-dom";
import { useTitle } from "@/hooks/useTitle";

const CDC = "https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html";
const ACVREP = "https://www.acvrep.org/newsitem?id=97";
const STEPS = [
  ["Teach by walking", "Walk the route once with the phone; Between Visit keeps the checkpoints and a memory of the space."],
  ["Client practises", "Between appointments your client walks it with smart glasses or a phone and hears the short cues you set."],
  ["Review and correct (memory v2)", "You review every cue that was spoken or held back and correct the route memory, which saves a new version."],
];

export default function Landing() {
  useTitle("Route practice between visits");
  return (
    <div className="bv-stack bv-landing" data-testid="landing-page">
      <section aria-labelledby="landing-heading">
        <h1 id="landing-heading" className="bv-h1" data-testid="landing-headline">Route practice between visits, reviewed by the specialist.</h1>
        <p className="bv-lead" data-testid="landing-subline">
          For independent orientation-and-mobility and low-vision practices. You teach a route once by walking it; your client practises between appointments with smart glasses or a phone; you review every cue and correct the route memory. You stay in charge.
        </p>
        <p className="bv-lead bv-lead-gap" data-testid="landing-research-line">
          7.1 million Americans have vision loss that glasses can't correct (<a href={CDC} className="bv-link" data-testid="landing-cdc-link">CDC, 2024 estimates</a>). All of North America has 4,068 certified vision-rehabilitation professionals (<a href={ACVREP} className="bv-link" data-testid="landing-acvrep-link">ACVREP, January 2025</a>).
        </p>
        <div className="bv-landing-actions">
          <Link to="/demo" className="bv-btn bv-btn-primary" data-testid="landing-try-demo-button">Try the demo</Link>
          <Link to="/workspace" className="bv-btn" data-testid="landing-workspace-button">Open the practice workspace</Link>
        </div>
      </section>
      <section aria-labelledby="steps-heading" className="bv-panel">
        <h2 id="steps-heading" className="bv-h2">How it works</h2>
        <ol className="bv-steps" data-testid="landing-steps">
          {STEPS.map(([title, text], i) => (
            <li key={title} data-testid={`landing-step-${i + 1}`}>
              <h3 className="bv-strong bv-step-title">{title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ol>
      </section>
      <p>
        <Link to="/research" className="bv-link" data-testid="landing-research-link">Read the research behind Between Visit</Link>
      </p>
    </div>
  );
}
