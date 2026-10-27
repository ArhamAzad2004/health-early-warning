# Sentinel Dubai — Implementation Plan

Team of 2–4, about seven days. The build pass has already delivered Day 0. Everything after that is tuning, polish and pitch. Keep the contract in `TRD.md` and `BACKEND_SCHEMA.md` as the single source of truth; if the code changes a weight, threshold or field name, change the doc in the same commit.

## Day 0 — done by the build pass

- Backend: seeded simulator, detection, playbook, privacy filter, back-test, live client; all six endpoints respond.
- Frontend: Overview (map, slider, alert feed, live strip, role switcher, banner), Alert detail, Validation, Privacy panel.
- At least scenario S1 visible end-to-end: slider to mid-July → Site A alert → detail → action card.
- Runs with `uvicorn app.main:app --reload --port 8000` (backend/) and `npm run dev` (frontend/).

## Day 1 — Make both scenarios honest

- Confirm S2 (late August, Al Quoz + Al Qusais + GBC Site B) fires and the district air-quality playbook is selected.
- Tune weights/threshold so both scenarios detect with lead time ≥ 2 days and false alarms ≤ 3; write the final numbers into `TRD.md` §4.
- Check missing-day gaps show as gaps (not zero) in `/api/signals` and on charts.
- Add a tiny test: `pytest` asserting both scenarios detected, no individual-level fields in any response, suppression of 1–4.

## Day 2 — Back-test and validation page

- Verify latency-aware replay: a signal with latency 3 must not be visible on day D for dates > D−3.
- Fill all metrics: sensitivity, PPV, false alarms, median latency, missing-input columns (without `incidents`, without `aqi`), impact estimate with visible assumptions.
- Validation page reads cleanly in one minute: four tiles, scenario table, comparison table, impact card.

## Day 3 — Dashboard polish

- Map: circle size/colour by level, outline, tooltip with level word, click → popup → open alert.
- Slider: play/pause, keyboard arrows, large date readout.
- Alert detail: contribution bars with contributing days, timeline with baseline band and shaded window, "<5" ticks.
- Empty/error states from `APP_FLOW.md` §6. Apply `DESIGN_BRIEF.md` colours and labels.

## Day 4 — Privacy and roles

- Role scope enforced in the API (404 outside scope), not only hidden in the UI.
- `public` role: districts, environmental signals and advisory text only; no counts.
- Banner on every page; governance panel text finished; toast on role change.
- Re-run the Day 1 test with each role.

## Day 5 — Pitch deck and demo video

- 8–10 slides: problem, concept, six-requirement map (one slide each or one table), architecture, validation numbers, limits, next steps.
- Record a 3–4 minute screen capture following the demo script in `PRD.md` §8; keep a backup recording in case the live demo fails.
- README with screenshots, run commands, and the limits paragraph.

## Day 6 — Buffer and rehearsal

- Full rehearsal twice, once with the backend offline from Open-Meteo (fallback strip).
- Fix anything that breaks the click path. Freeze the seed and the weights.

## Day 7 — Stretch goals (only if Days 1–6 are green)

1. **Claude-written alert briefings**: one plain-language paragraph per alert generated from the alert JSON, clearly marked as AI-drafted, cached at startup.
2. **Real open-data baselines**: replace synthetic district visit baselines with published Dubai health statistics where available.
3. **Postgres**: persist `observation`, `score`, `alert` tables per `BACKEND_SCHEMA.md`; keep in-memory as default.
4. **Auth**: real roles behind login; `audit_log` table recording who viewed what.

## Team split

| Person | Owns | Days |
|---|---|---|
| A — Backend/detection | Simulator, detection tuning, back-test, tests | 1, 2, 6 |
| B — Frontend | Map, slider, alert detail, validation page, design brief | 2, 3, 4 |
| C — Privacy/story | Role scope, governance text, README, deck, demo script, video | 4, 5, 6 |
| D (optional) — Stretch | Claude briefings or Postgres; otherwise pairs with B on polish | 3–7 |

With two people: A takes rows A + C's backend parts; B takes rows B + deck/video. Daily 15-minute sync on the demo click path.

## Definition of done for demo day

- [ ] `uvicorn` and `npm run dev` start clean from a fresh clone in under two minutes following the README.
- [ ] Both scenarios detected; lead times, sensitivity, PPV, false alarms, median latency visible on Validation page.
- [ ] Missing-input columns show a measurable change when `incidents` or `aqi` is removed.
- [ ] Every alert shows action, responsible role, notify role, evidence table, assumptions, completeness %, confidence.
- [ ] Contribution bars show at least four signal types for S1 and three for S2.
- [ ] Role switch: `employer_hse` sees sites only; `public` sees districts only; API returns 404 outside scope.
- [ ] A "<5" suppressed cell is visible somewhere in the demo path.
- [ ] Boundary banner visible on all pages; governance panel complete.
- [ ] Live strip shows real Dubai values, and shows the fallback cleanly when offline.
- [ ] Map circles colour-blind safe with text labels; charts have text summary lines.
- [ ] Demo script rehearsed twice under 5 minutes; backup video recorded.
- [ ] README states clearly: synthetic health/work data, real weather, no causal claims.
- [ ] Public GitHub repo `health-early-warning` pushed with docs/, backend/, frontend/.
