# Phase 19 Journeys
- JRN-242: steps: in the route builder, give two checkpoints near-identical texts. expected: both cards show "Reads like checkpoint N. Add what is different here (a sign, a door, a turn, a sound)."; Approve and Save still work.
- JRN-243: steps: use two very similar photos with different texts. expected: the warning appears via photo similarity.
- JRN-244: steps: press "Suggest a different description". expected: a new ≤25-word text naming what is unique, labelled "Suggested by AI"; the checkpoint becomes unapproved; on a re-check the warning clears if the texts now differ.
- JRN-245: steps: force an AI failure. expected: "AI suggestion unavailable"; the text is unchanged.
- JRN-246: steps: the same warning in the teach review and in scan placement. expected: the same behaviour.
- JRN-247: steps: open the demo route v1 and v2 (version history / memory endpoint). expected: three distinct texts (entrance door + handrail start / right turn corner / reception desk); no warnings.
- JRN-248: steps: 2 replays each on v1 and v2. expected: the chair is spoken on v1, held back on v2; checkpoints progress in order.
- JRN-249: steps: checker unit cases. expected: the old identical texts are flagged; 5 distinct texts aren't.
