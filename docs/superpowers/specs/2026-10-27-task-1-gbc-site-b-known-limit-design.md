# Design — Task 1: GBC Site B missed in the dust-storm scenario (S2)

- **Date:** 2026-10-27
- **Source:** GitHub issue [#1 — Decide how to handle GBC Site B being missed in the dust-storm scenario](https://github.com/ArhamAzad2004/health-early-warning/issues/1) (label: `backend`, milestone: Demo day)
- **Decision (approved):** **Option A — accept and explain.** The GBC Site B miss in scenario S2 is accepted as a known limit and surfaced honestly on the Validation page. No detection-engine, simulator, weight, or threshold changes.

## Problem

- Scenario S2 (dust-storm respiratory spike, 2025-08-21 → 2025-09-06, peak 2025-08-30) lists affected areas `["al_quoz", "al_qusais", "gbc_site_b"]`.
- GBC Site B was the area **not** alerted: its best in-window day reached risk ≈ 5.1 with 2 corroborating signals, but never on two consecutive gated days (risk ≥ 4.5, ≥2 signals at smoothed z ≥ 1.5), so no alert opened.
- Districts `al_quoz` / `al_qusais` alerted correctly via `resp_visits` + `lab_resp_pos`.
- Root cause: during S2 a site has only its workplace `absence` signal at site level; there is no site-level clinical signal to corroborate the dust-driven absence bump. The environmental AQI of the parent district corroborates, but the consecutive-day gate was not met.

## Considered options

1. **Option A — Accept and explain (chosen).** Keep detection honest; surface the miss as a known limit.
2. **Option B — Raise Site B's absence effect in `backend/app/sim.py`.** Tunable alternative; rejected for now (risk of tuning toward the demo; corroboration design is intentional).
3. **Option C — Loosen the corroboration rule.** Explicitly ruled out by the issue.

## Design (Option A)

### Backend — `backend/app/engine.py`

- In `_metrics`, compute per scenario: `missed_areas` = sorted affected areas with no overlapping alert (`set(sc["areas"]) - set(areas_hit)`).

### Backend — `backend/app/main.py`

- No change required; `/api/backtest` returns the extended scenario records (additive field).

### Backend — tests — `backend/tests/test_engine.py`

- Assert S2 reports `missed_areas == ["gbc_site_b"]` and S1 reports none.
- Keep scenario-level detection assertions (`sensitivity == 1.0`) unchanged — S2 remains "detected" via district alerts.

### Frontend — `frontend/src/Validation.jsx`

- For scenarios with missed areas, render a known-limit note (e.g. "Known limit — Dust storm respiratory spike (Al Quoz, Al Qusais): GBC Site B – Al Quoz not alerted.").
- Map missed area ids to display names via the existing `/api/areas` endpoint.

### Docs — no numeric changes expected; wording updated

- `README.md`, `docs/PRD.md` (§7, §9, §10), `docs/TRD.md` (§7, §11), `CLAUDE.md`.

## Verification

- Re-run back-test: sensitivity stays 1.0; S2 `missed_areas == ["gbc_site_b"]`; all other numbers unchanged (PPV 0.8, 1 false alarm, lead times S1 5 / S2 3).

## Out of scope

- Any change to corroboration rule, weights, thresholds, or simulator dynamics.
- Real-data baselines, Postgres, auth (stretch goals / later tasks).
