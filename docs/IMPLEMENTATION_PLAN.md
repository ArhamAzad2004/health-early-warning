# Sentinel Dubai — Implementation Plan

Team of 2–4, about seven days. The build pass has delivered Day 0 (backend complete, frontend in progress). Everything after that is tuning, polish and pitch. `TRD.md` and `BACKEND_SCHEMA.md` mirror `backend/app/sim.py`, `engine.py` and `main.py`; if the code changes a constant, field name or playbook string, change the doc in the same commit.

## Day 0 — done by the build pass

- Backend: seeded simulator (`sim.py`), latency-aware detection with corroboration and persistence (`engine.py`), playbook, back-test with missing-input re-runs, calibration sweep and impact estimate, role scope, suppression, Open-Meteo client (`main.py`). Seven endpoints respond.
- Current back-test: sensitivity 1.0, area sensitivity 0.8 (GBC Site B not alerted in S2), PPV 0.8, 1 false alarm (Al Quoz heat, late June), lead time S1 5 days, S2 3 days.
- Frontend: Overview (map, slider, alert feed, live strip, role switcher, banner), Alert detail, Validation, Privacy pages being wired to the API.
- Runs with `uvicorn app.main:app --reload --port 8000` (backend/) and `npm run dev` (frontend/).

## Day 1 — Decide what "honest" looks like

- Decide whether GBC Site B (absence-only signal in S2) should be detected. Options: accept and explain on the Validation page as a known limit of a single-signal site, or raise Site B's absence effect in `sim.py` — do not lower the corroboration rule to get it.
- Look at the Al Quoz late-June false alarm; keep it (it is a credible heat pattern) and say so in the pitch.
- Add a small `pytest`: both scenarios detected; no response key ever names a person; a 1–4 count is suppressed in `/api/signals` and in alert evidence; `public` gets 403 on `/api/backtest` and 404 on a site.
- Write the final numbers into `PRD.md` §9 and `TRD.md` §7 if anything moved.

## Day 2 — Validation page polish

- Six metric tiles, scenario table, five missing-input rows, seven calibration rows with 4.5 highlighted, impact card with the three assumption sentences beside the numbers.
- One-sentence reading guide under each table so a judge needs no explanation.

## Day 3 — Dashboard polish

- Map: circle size/colour by level with the level word, outline, tooltip, click → popup (level, risk, missing signals) → open alert.
- Slider: play/pause, keyboard arrows, large date readout; reads `start`/`end`/`levels` from `/api/meta`.
- Alert detail: contribution bars in API order, timeline with baseline band and shaded window, "<5" ticks, missing gaps, risk line with the three thresholds.
- Empty/error states from `APP_FLOW.md` §6. Apply `DESIGN_BRIEF.md` colours and labels.

## Day 4 — Privacy and roles

- Confirm every page respects role scope purely from API responses (no client-side data the role should not have).
- `public`: districts, environmental charts and advisory text only; Validation shows the 403 message.
- Banner on every page; governance panel text finished; toast on role change.
- Re-run the Day 1 test with each role.

## Day 5 — Pitch deck and demo video

- 8–10 slides: problem, concept, six-requirement map, architecture, validation numbers (including the missed Site B and the one false alarm), limits, next steps.
- Record a 3–4 minute screen capture following `PRD.md` §8; keep it as backup for the live demo.
- README with screenshots, run commands, and the limits paragraph.

## Day 6 — Buffer and rehearsal

- Full rehearsal twice, once with Open-Meteo unreachable (`ok: false` fallback strip).
- Fix anything that breaks the click path. Freeze seed, weights and thresholds.

## Day 7 — Stretch goals (only if Days 1–6 are green)

1. **Claude-written alert briefings**: one plain-language paragraph per alert generated from the alert JSON, clearly marked as AI-drafted, cached at startup.
2. **Real open-data baselines**: replace synthetic district visit baselines with published Dubai health statistics where available.
3. **Postgres**: persist `observation`, `score`, `alert` tables per `BACKEND_SCHEMA.md`; keep in-memory as default.
4. **Auth and roles**: real login; dedicated Occupational Health Inspector role; `audit_log` table recording who viewed what.

## Team split

| Person | Owns | Days |
|---|---|---|
| A — Backend/detection | Site B decision, tests, any tuning, back-test numbers | 1, 2, 6 |
| B — Frontend | Map, slider, alert detail, validation page, design brief | 2, 3, 4 |
| C — Privacy/story | Role checks, governance text, README, deck, demo script, video | 4, 5, 6 |
| D (optional) — Stretch | Claude briefings or Postgres; otherwise pairs with B on polish | 3–7 |

With two people: A takes rows A + C's role checks; B takes rows B + deck/video. Daily 15-minute sync on the demo click path.

## Definition of done for demo day

- [ ] `uvicorn` and `npm run dev` start clean from a fresh clone in under two minutes following the README.
- [ ] Both scenarios detected; sensitivity, area sensitivity, PPV, false alarms, median latency, lead times visible on the Validation page.
- [ ] Missing-input table shows five rows with a visible change in lead time or false alarms for at least two of them.
- [ ] Calibration table shows why watch = 4.5.
- [ ] Every alert shows action, roles, category, evidence table, assumptions, completeness and confidence.
- [ ] Site A alert shows the 20–22 July absence outage as missing (gap, lower completeness), not as zero.
- [ ] Role switch: `employer_hse` sees sites only; `public` sees districts only, advisories only, no Validation; API returns 404 outside scope.
- [ ] A "<5" suppressed cell is visible somewhere in the demo path.
- [ ] Boundary banner visible on all pages; governance panel complete.
- [ ] Live strip shows real Dubai values, and shows the fallback cleanly when `ok` is false.
- [ ] Map circles colour-blind safe with the level word; charts have text summary lines.
- [ ] Demo script rehearsed twice under 5 minutes; backup video recorded.
- [ ] README states clearly: synthetic health/work data, real weather, no causal claims, Site B missed.
- [ ] Public GitHub repo `health-early-warning` pushed with docs/, backend/, frontend/.
