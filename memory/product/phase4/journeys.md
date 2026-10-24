# Phase 4 Journeys
(Earlier journeys stay valid except where superseded.)

- JRN-48: steps: open Routes. expected: "Check route (synthetic)", "Library entrance (synthetic)" and "Test route (synthetic)" are not listed; their photos no longer load (404). superseded: [JRN-33]
- JRN-49: steps: open /device-test and run tests/wss_ingest_check.py. expected: "att-test" still works as in Phase 2.
- JRN-50: steps: open an unsaved route. expected: no "Assign exercise" button. Open a saved route: the button is visible.
- JRN-51: steps: open the Assign form. expected: lists both clients; Standard is selected; both silence boxes are checked; the stop rule is prefilled with "If you feel unsure, stop, press Help and wait for my call."
- JRN-52: steps: submit with no client or an empty goal. expected: blocked with field messages; nothing created.
- JRN-53: steps: assign to Client A with a goal. expected: a confirmation with the run link "/run/<id>#key=<key>", stream ID matching att-xxxx, the key, 3 working copy buttons, "The client also sees these on their run page." and a shown-once warning.
- JRN-54: steps: close the confirmation, open Client A's page. expected: the exercise shows goal, route name, version, "Standard"; the attempt shows status "not_started", the stream ID and run link /run/<id> without a key; no key anywhere on the page or in its API response.
- JRN-55: steps: press "New attempt". expected: a one-time confirmation with a different stream ID and key; both attempts are listed.
- JRN-56: steps: save the route as a new version, return to the client page. expected: the exercise still shows the old pinned version.
- JRN-57: steps: open the run link with #key. expected: the goal, stream ID and key are shown; the server logs never show the key.
- JRN-58: steps: open /run/<id> with no fragment, with a wrong #key, and /run/nope. expected: "This link is missing its key. Ask your practitioner for a new attempt.", "This link's key isn't valid." and "Run not found" in turn.
- JRN-59: steps: connect wss://<public>/api/ws/ingest/<new stream id>?key=<new key>. expected: connects, {"viewers":0}; a wrong key gives 1008.
- JRN-60: steps: open Client B's page. expected: "No exercises assigned yet".
- JRN-61: steps: view the form, confirmation, client page and run page at 390px. expected: no horizontal scroll; keyboard operable; footer present.
