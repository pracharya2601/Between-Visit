# Phase 16 Requirements: Landing Page Redesign
Version: phase-16

Goal: "/" should read like a product, not a document. Keep the facts, the footer and accessibility. Only "/" changes; every other page stays as is. See ../overview.md.

## Global
- REQ-515 [always] Max content width 1200 px, generous spacing, Atkinson Hyperlegible.
- REQ-516 [always] WCAG AA contrast everywhere (including white on navy, the caption card, the stats links).
- REQ-517 [always] One h1, logical heading order, keyboard order = visual order, the skip link works.
- REQ-518 [always] The unchanged footer disclaimer shall stay at the bottom.
- REQ-519 [always] On mobile, the sections shall stack, with the 3D view below the hero text.
- REQ-520 [always] No other page shall change.

## 1. Hero
- REQ-521 [always] The hero shall be full width on a dark navy background with white text.
- REQ-522 [always] The left side shall have the h1 "Route practice between visits, reviewed by the specialist." at 56–72 px (responsive smaller on mobile).
- REQ-523 [always] The left side shall have the subline "Teach a route once by walking it. Your client practises with smart glasses. You review every cue."
- REQ-524 [always] The left side shall have the buttons "Try the demo" (primary → /demo) and "Open the practice workspace" (→ /workspace).
- REQ-525 [always] The right side shall show the live 3D corridor of the demo route using the same three.js view as the replay, looping the stored demo trail with the moving marker + heading arrow.
- REQ-526 [always] The hero loop shall be scripted from existing stored data (trail, cue positions, known entity); it creates no attempts and makes no AI calls. (interpreted)
- REQ-527 [always] The loop shall alternate passes: v1 pass → at the chair, an amber dot + a floating caption card "Spoken: Chair ahead, about 2 metres."; v2 pass → the purple chair triangle visible, a grey dot + card "Held back: Known, chair confirmed in v2". (interpreted)
- REQ-528 [always] The 3D view shall lazy-load after the text renders and use a lighter point set (~15k points, interpreted); the headline is visible immediately.
- REQ-529 [state] While prefers-reduced-motion is set, or WebGL is unavailable, or the 3D fails to load, the system shall show a still image of the same view (with the caption card) instead.
- REQ-530 [always] The 3D/still shall have a descriptive aria-label/alt; the caption card is decorative for screen readers or announced politely, never assertive. (interpreted)
- REQ-531 [always] The hero 3D shall not capture keyboard focus or scroll/zoom (no orbit controls on the landing). (interpreted)

## 2. Stats band
- REQ-532 [always] The stats band shall show the big number "7.1M" with "Americans with vision loss glasses can't correct" and a small link "CDC, 2024 estimates" → https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html.
- REQ-533 [always] The stats band shall show the big number "4,068" with "certified vision-rehab professionals in all of North America" and a small link "ACVREP, Jan 2025" → https://www.acvrep.org/newsitem?id=97.
- REQ-534 [always] The stats band shall show a third line: "1,700+ people with uncorrectable vision loss in the US for every certified professional in North America".
- REQ-535 [always] The band shall link to /research ("See the research").

## 3. How it works
- REQ-536 [always] There shall be three numbered cards with real stills captured from the app: (1) Teach by walking (the teach-walk 3D review), (2) Client practises (the client run screen with the big caption), (3) Review and correct (the review page with the Spoken / Held back timeline). Each has a short title, one sentence and meaningful alt text.
- REQ-537 [always] The stills shall be static optimised images (WebP/PNG, lazy-loaded, ≤200 KB each, interpreted) bundled with the frontend; any data created to capture them is deleted.

## 4. What the specialist sees
- REQ-538 [event] When the section loads, it shall fetch 2–3 rows from the existing demo review data (e.g. a spoken chair cue, a held-back "Not repeated…" and a "Held back: another cue…" row) and show them with time, text and plain-word reasons, plus a link "Open the full review".
- REQ-539 [unwanted] If the fetch fails, then the section shall hide quietly (no error on the landing).

## 5. Closing band
- REQ-540 [always] A closing band shall show "Try the demo" (→ /demo), then the unchanged footer.

## Fixes after 12c (Phase 16b)
- REQ-541 [event] When a checkpoint is reached during a replay (a spoken checkpoint cue), the replay screen shall update "Last checkpoint" text, the screen-reader summary, and the 3D marker (reached = filled).
- REQ-542 [always] "Reached" shall reflect the cue engine (checkpoint cue spoken), never be faked from position alone. If the pipeline doesn't reach checkpoints 2 and 3 on the synthetic frames, the fix belongs in the frames (REQ-543), and the builder shall report the cause.
- REQ-543 [always] No synthetic demo frame shall show a date stamp or camera UI. Crop or regenerate the affected frames, keeping the same corridor content, the chair between checkpoints 1–2, and visible landmarks for Hallway turn and Reception desk. Regenerated frames pass both person checks; old frames become unservable.
- REQ-544 [always] After the frame changes, v1 shall still speak the chair (2/2) and v2 shall still hold it back as known (2/2).
- REQ-545 [always] The landing hero 3D view shall be at least 55% of the hero width and at least 420 px tall on desktop.
- REQ-546 [always] The caption card shall be visible over the 3D view, alternating between "Spoken: Chair ahead, about 2 metres." and "Held back: Known, chair confirmed in v2"; the still fallback shows the card too. 1440×900 and 1920×1080 stay above the fold for the headline + buttons.

## Quality requirements
```
Q-72 Tag: Landing.Speed
     Scale: seconds to the visible headline (LCP) on a fresh load
     Meter: headless timing
     Must: 2.5   Plan: 1.2
Q-73 Tag: Landing.A11y
     Scale: axe serious/critical violations on "/" (default + reduced motion + mobile)
     Meter: axe
     Must: 0   Plan: 0
Q-74 Tag: Landing.Visual
     Scale: hero 3D + caption card visible above the fold at 1920×1080 and 1440×900
     Meter: screenshot
     Must: yes   Plan: yes
```
