# Phase 21 Requirements: Landing Page Redesign v2 (public "/" only)
Version: phase-21

Scope: ONLY frontend/src/pages/Landing.jsx, components/landing/HeroVisual.jsx, HeroScene.jsx, SpecialistRows.jsx, and the bv-l-* / bv-hero-* styles in App.css. Nothing else changes (no other route/page/API/backend/DB, /demo, /workspace, /review, /research, Layout.jsx, shared Scene3D). No new dependencies, no stock photos, no invented numbers, testimonials, outcomes or partners.

## Must keep
- REQ-633 [always] Keep HeroScene's lazy WebGL loading, error boundary and the hero-still.webp fallback.
- REQ-634 [always] Keep all data-testids, the skip link, Atkinson Hyperlegible, the CDC and ACVREP links, and the existing screenshots + alt text.
- REQ-635 [always] Keep the site footer disclaimer as it is, visually separate.

## Look
- REQ-636 [always] Palette: graphite #0b0d10 main, deep navy secondary, warm off-white #f5f2ea for reading sections, safety yellow #f5c400 for the primary button, route line, checkpoints and key facts; green only for spoken/confirmed; amber only for held-back. No magenta or purple anywhere on "/" (the HeroScene route line → yellow; the known chair → amber).
- REQ-637 [always] Large editorial type, a strong grid, generous spacing, few cards, no heavy borders, shadows or gradients.
- REQ-638 [always] Recurring motif: a thin yellow route line with round checkpoint nodes in the hero, between sections, in the steps and in the final CTA.

## Sections (in order)
- REQ-639 [always] 1) Hero (dark, asymmetric): the 3D route view ≥60% width on desktop, full width under the text on mobile, reserved aspect ratio (never an empty black box), a clearer camera angle, a yellow route, 2–3 numbered checkpoint nodes, the existing cycling spoken/held-back annotation card. h1 "Teach the route once. Review every decision." Sub "Between Visit turns a walked route into specialist-approved spatial memory for practice between appointments." A yellow primary button "Watch the 20-second demo" → /demo; a text link "Open the specialist workspace" → /workspace.
- REQ-640 [always] 2) Problem (off-white): "O&M specialists teach a route in person, but clients practise alone between visits and the specialist cannot see how it went." (one or two sentences)
- REQ-641 [always] 3) Demo strip: the hero-still and/or the v1 vs v2 comparison side by side, "v1: chair announced" vs "v2: chair confirmed by specialist, held back", with a link to /demo.
- REQ-642 [always] 4) The Teach → Practise → Review journey, joined by the yellow route line (vertical on mobile), each with its existing screenshot and the exact lines: TEACH "The specialist walks the route and approves the proposed checkpoints." PRACTISE "The client follows it with smart glasses or a phone. It stays quiet unless a cue helps." REVIEW "The specialist sees what was spoken, what was held back and why, and corrects the route memory."
- REQ-643 [always] 5) What the specialist learns (SpecialistRows simplified): one spoken row, one held-back row with its reason (from the existing demo data), then "Specialist confirms the chair; route memory saved as v2.", and keep "Open the full review".
- REQ-644 [always] 6) Human context: a short paragraph (the specialist decides the route, the glasses are a quiet tool, the client practises at their own pace); a single image constant (HUMAN_PHOTO = null); while empty, a text-only layout with no placeholder box.
- REQ-645 [always] 7) Research (off-white): 7.1M (CDC, 2024 estimates, the current wording) and 4,068 (ACVREP, Jan 2025, certified professionals across North America) with links; replace the ratio sentence with exactly: "These figures cover different populations (US prevalence vs North American certifications), so they are not a precise caseload ratio, but they show how few certified professionals there are."; keep "See the research" → /research.
- REQ-646 [always] 8) Professional safeguards as a clear list section: Specialist-approved indoor routes only; Experimental practice tool; A human reviews every AI observation; Stops and asks for help when unsure; Does not replace a cane, guide dog or O&M specialist; Not a medical or safety device.
- REQ-647 [always] 9) Final CTA (dark, with the route motif): "See one route become measurable practice." + a yellow button "Try the 20-second demo" → /demo.

## Truthfulness
- REQ-648 [always] "20-second demo" must be true: the builder shall measure the demo replay length (Start → end). If it isn't about 20 s (±5 s), report it before shipping that wording. (interpreted)

## Motion & accessibility
- REQ-649 [always] Motion only for route-line drawing, the checkpoint confirm, and the v1 → v2 change; all off under prefers-reduced-motion; the page reads fully without motion.
- REQ-650 [always] WCAG AA contrast (no yellow text on off-white; dark text on yellow buttons), visible focus rings, one h1 then an h2 per section, touch targets ≥48 px, no horizontal scroll at 360 px.
- REQ-651 [always] Check at desktop 1440, tablet 768 and mobile 375 (and 360 for overflow).
- REQ-652 [always] The hero still makes no AI calls and creates no attempts.
