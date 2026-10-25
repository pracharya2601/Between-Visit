import { Link, NavLink } from "react-router-dom";

const NAV = [["/clients", "Clients"], ["/routes", "Routes"]];

export const FOOTER_TEXT =
  "Experimental practice tool used under the practitioner's direction. It doesn't replace the cane, the dog guide or the specialist, and it isn't a safety device.";

export default function Layout({ children, nav = true, home }) {
  const logoTo = home ?? (nav ? "/workspace" : null);
  return (
    <div className="bv-shell">
      <a href="#main-content" className="bv-skip" data-testid="skip-to-content-link">
        Skip to main content
      </a>
      <header className="bv-header" aria-label="Site header" data-testid="site-header">
        <div className="bv-wrap bv-header-row">
          {logoTo ? (
            <Link to={logoTo} className="bv-brand" data-testid="brand-home-link">Between Visit</Link>
          ) : (
            <span className="bv-brand" data-testid="brand-name">Between Visit</span>
          )}
          {nav && <nav aria-label="Main navigation" data-testid="top-nav">
            <ul className="bv-nav">
              {NAV.map(([to, label]) => (
                <li key={to}>
                  <NavLink to={to} className="bv-nav-link" data-testid={`nav-${label.toLowerCase().replace(" ", "-")}`}>{label}</NavLink>
                </li>
              ))}
            </ul>
          </nav>}
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="bv-main" aria-label="Main content" data-testid="main-content">
        <div className="bv-wrap">{children}</div>
      </main>
      <footer className="bv-footer" aria-label="Site footer" data-testid="site-footer">
        <div className="bv-wrap">
          <p data-testid="footer-disclaimer">{FOOTER_TEXT}</p>
        </div>
      </footer>
    </div>
  );
}
