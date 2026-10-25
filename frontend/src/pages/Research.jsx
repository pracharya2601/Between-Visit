import { useTitle } from "@/hooks/useTitle";

const CDC = "https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html";
const ACVREP = "https://www.acvrep.org/newsitem?id=97";
const DOI = "https://doi.org/10.1145/3555622";

export default function Research() {
  useTitle("Research");
  return (
    <div className="bv-stack" data-testid="research-page">
      <h1 className="bv-h1" data-testid="research-heading">Research behind Between Visit</h1>
      <section aria-labelledby="cdc-heading" className="bv-panel" data-testid="research-cdc">
        <h2 id="cdc-heading" className="bv-h2">CDC VEHSS Modeled Estimates, 2024</h2>
        <ul className="bv-list">
          <li>7,149,000 people in the United States with best-corrected vision loss</li>
          <li>706,000 people who are blind</li>
        </ul>
        <p><a href={CDC} className="bv-link" data-testid="research-cdc-link">CDC: vision loss prevalence estimates</a></p>
      </section>
      <section aria-labelledby="acvrep-heading" className="bv-panel" data-testid="research-acvrep">
        <h2 id="acvrep-heading" className="bv-h2">ACVREP</h2>
        <ul className="bv-list">
          <li>4,068 certified vision-rehabilitation professionals in North America</li>
          <li>9.5 million adults with visual impairment expected within five years</li>
        </ul>
        <p><a href={ACVREP} className="bv-link" data-testid="research-acvrep-link">ACVREP news item, January 2025</a></p>
      </section>
      <section aria-labelledby="dove-heading" className="bv-panel" data-testid="research-dove">
        <h2 id="dove-heading" className="bv-h2">Dove et al., NYU, Proc. ACM HCI (CSCW) 2022</h2>
        <p className="bv-strong">"Digital Technologies In Orientation And Mobility Instruction For People Who Are Blind Or Have Low Vision"</p>
        <ul className="bv-list">
          <li>Interviews with 11 certified orientation and mobility specialists (COMS).</li>
          <li>In-person O&amp;M instruction is "time-consuming and labor-intensive".</li>
          <li>A shortage of specialists "has accelerated interest in remote instruction and assessment".</li>
          <li>Named opportunities: "highlighting clients' progress towards O&amp;M goals" and "monitoring clients' independent travel progress".</li>
        </ul>
        <p><a href={DOI} className="bv-link" data-testid="research-dove-link">Read the paper by Dove et al. (doi.org/10.1145/3555622)</a></p>
      </section>
      <section aria-labelledby="validating-heading" className="bv-panel" data-testid="research-validating">
        <h2 id="validating-heading" className="bv-h2">Still validating with practitioners</h2>
        <ul className="bv-list" aria-labelledby="validating-heading" data-testid="research-validating-list"></ul>
        <p data-testid="research-validating-empty">Nothing listed yet.</p>
      </section>
    </div>
  );
}
