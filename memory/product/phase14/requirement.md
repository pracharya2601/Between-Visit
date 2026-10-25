# Phase 14 Requirements: Polish (no new features)
Version: phase-14

Goal: a public-facing landing and research page, clean demo naming, a tidier nav, and an accessibility + copy pass, while keeping every existing flow working. See ../overview.md. Phases 1–13 must keep working.

## Landing page "/"
- REQ-460 [always] "/" shall show the headline (h1) "Route practice between visits, reviewed by the specialist."
- REQ-461 [always] "/" shall show the subline: "For independent orientation-and-mobility and low-vision practices. You teach a route once by walking it; your client practises between appointments with smart glasses or a phone; you review every cue and correct the route memory. You stay in charge."
- REQ-462 [always] "/" shall show the research line "7.1 million Americans have vision loss that glasses can't correct (CDC, 2024 estimates). All of North America has 4,068 certified vision-rehabilitation professionals (ACVREP, January 2025)." with "CDC, 2024 estimates" linking to https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html and "ACVREP, January 2025" linking to https://www.acvrep.org/newsitem?id=97.
- REQ-463 [always] "/" shall show three short steps: "Teach by walking" / "Client practises" / "Review and correct (memory v2)", each with one plain sentence. (interpreted)
- REQ-464 [always] "/" shall show the buttons "Try the demo" (primary → /demo) and "Open the practice workspace" (→ /workspace).
- REQ-465 [always] "/" shall show a link to /research.
- REQ-466 [always] The previous home content (practice, practitioner, clients, links) shall move to /workspace.
- REQ-467 [always] Inside the practitioner workspace the logo shall go to /workspace; on public pages (landing, demo, replay, research) it shall go to "/".
- REQ-468 [always] Existing deep links (/clients, /routes, /review/…, /run/…, /device-test, /replay/…) shall keep working.

## Research page "/research"
- REQ-469 [always] The page shall list: CDC VEHSS Modeled Estimates, 2024: 7,149,000 people with best-corrected vision loss, 706,000 blind, with a link to https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html.
- REQ-470 [always] The page shall list: ACVREP: 4,068 certified professionals in North America; 9.5 million adults with visual impairment expected within five years, with a link to https://www.acvrep.org/newsitem?id=97.
- REQ-471 [always] The page shall list: Dove et al., NYU, Proc. ACM HCI (CSCW) 2022, "Digital Technologies In Orientation And Mobility Instruction For People Who Are Blind Or Have Low Vision" (https://doi.org/10.1145/3555622): interviews with 11 COMS; in-person O&M is "time-consuming and labor-intensive"; a shortage of specialists "has accelerated interest in remote instruction and assessment"; named opportunities "highlighting clients' progress towards O&M goals" and "monitoring clients' independent travel progress". Quotes are exact (verified against the paper).
- REQ-472 [always] The page shall have a section "Still validating with practitioners" with an empty list and the text "Nothing listed yet." (interpreted)
- REQ-473 [always] External links shall open normally with descriptive link text (not "click here").

## Demo data renames (one-off clean-up of synthetic demo data, user-approved exception to "history never rewritten")
- REQ-474 [event] When the migration runs, the system shall rename the route "Review demo route 3D (synthetic)" to "Entrance → hallway turn → reception desk (synthetic)".
- REQ-475 [event] When the migration runs, the system shall rename that route's checkpoints in order to "Entrance", "Hallway turn", "Reception desk" in the checkpoints collection, in ALL its route_versions snapshots, the synthetic recording metadata, and past event/cue texts and fields that mention the old names (e.g. "Checkpoint 1: …", checkpoint_match, checkpoint).
- REQ-476 [event] When the migration runs, the system shall rename "Review demo route 2D (synthetic)" to "Lobby to elevator (synthetic)".
- REQ-477 [always] The migration shall be idempotent, logged, and touch only these two demo routes.
- REQ-478 [always] "Try the demo" shall point to the renamed 3D route; the v1 → v2 chair story shall still work.

## Navigation
- REQ-479 [always] "Device test" shall be removed from the nav and from /workspace; /device-test shall still work at its URL.

## Accessibility pass (every page)
- REQ-480 [always] Every page shall have exactly one h1 and a logical heading order with no skipped levels.
- REQ-481 [always] All text shall meet WCAG AA contrast (aim AAA), including disabled, placeholder, badge and link text.
- REQ-482 [always] Every control shall have an accessible name.
- REQ-483 [always] The focus order shall follow the visual order, with visible focus everywhere and no focus traps (dialogs trap and restore focus correctly).
- REQ-484 [always] The skip link shall work on every page.
- REQ-485 [always] Each page shall have a unique, descriptive document title.
- REQ-486 [always] Fixes shall be made in place; the builder shall list what it found and fixed per page.

## Copy audit
- REQ-487 [always] No UI text, page or prompt-visible copy shall claim safety, obstacle avoidance, hazard detection, navigation guarantees or "safe route" (e.g. replace "obstacle" with "object" where shown to users, interpreted).
- REQ-488 [always] The footer disclaimer shall stay on every page, verbatim.

## Fresh-session check
- REQ-489 [always] In a fresh private browser context (no cookies/localStorage): landing → Try the demo → replay plays → review link opens shall work end to end.

## Quality requirements
```
Q-65 Tag: A11y.Automated
     Scale: axe-core serious/critical violations per page
     Meter: axe on landing, research, workspace, clients, client, routes, builder, teach, review, run, replay, demo
     Must: 0   Plan: 0
Q-66 Tag: Copy.Claims
     Scale: user-visible strings claiming safety/obstacle avoidance
     Meter: grep the frontend + rendered pages
     Must: 0   Plan: 0
Q-67 Tag: Regression
     Scale: earlier check scripts failing
     Meter: re-run the existing scripts (wss, run API, vision, depth, policy replays, replay)
     Must: 0   Plan: 0
```
