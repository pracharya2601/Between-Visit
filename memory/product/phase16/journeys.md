# Phase 16 Journeys
(Only "/" changes; earlier journeys stay valid except JRN-191, which is superseded for layout.)

- JRN-213: steps: open "/" at 1920×1080. expected: a navy full-width hero; the h1 at 56–72 px, the subline, two buttons on the left; the 3D corridor with the moving marker on the right, above the fold. superseded: [JRN-191 layout]
- JRN-214: steps: watch the hero loop for two passes. expected: v1 pass → an amber dot + "Spoken: Chair ahead, about 2 metres."; v2 pass → the purple chair triangle + a grey dot + "Held back: Known, chair confirmed in v2"; no attempts are created, no AI calls (check the network/DB).
- JRN-215: steps: emulate prefers-reduced-motion, then disable WebGL. expected: a still image of the same view with the caption card each time.
- JRN-216: steps: look at the stats band. expected: "7.1M" + CDC link, "4,068" + ACVREP link, "1,700+ people with uncorrectable vision loss in the US for every certified professional in North America", a research link.
- JRN-217: steps: look at How it works. expected: three numbered cards with real app stills (teach 3D review, run screen caption, review timeline) and alt text.
- JRN-218: steps: look at What the specialist sees. expected: 2–3 live rows from the demo review with plain-word reasons; "Open the full review" works; with the API blocked the section hides.
- JRN-219: steps: the closing band. expected: "Try the demo", then the verbatim footer.
- JRN-220: steps: Tab through "/". expected: the skip link first, then logical order; the 3D doesn't trap focus; one h1; axe 0 serious/critical.
- JRN-221: steps: open "/" at 390 px. expected: sections stacked; the 3D below the hero text; no horizontal scroll.
- JRN-222: steps: open /demo, /workspace, /research. expected: unchanged.
