# Sentinel Dubai — Roadmap

Solo portfolio project. `TRD.md` and `BACKEND_SCHEMA.md` mirror `backend/app/sim.py`, `engine.py` and `main.py`; if the code changes a constant, field name or playbook string, change the doc in the same pull request.

## Done

- Seeded Dubai simulator, latency-aware detection with corroboration and persistence, rule-based playbook.
- Back-test with calibration sweep, missing-input re-runs and impact estimate; current result: both scenarios detected 5 and 3 days before peak, PPV 0.8, 1 false alarm, GBC Site B missed (known limit).
- Dashboard: map with replay and jump-to-scenario buttons, alert detail, validation, privacy pages; live Dubai weather.
- Privacy: aggregation, small-cell suppression (including baseline/z on hidden cells), role-based views.
- Engineering: CI (tests, build, Docker smoke test), one-command setup (`npm run setup`, `npm run dev`, `npm test`), Render deploy config, locked headline numbers in tests.

## v1.0 portfolio release

Tracked as GitHub issues under the **v1.0 portfolio release** milestone. In rough priority order:

1. ~~Public live link on Render.~~ Done: https://sentinel-dubai.onrender.com
2. ~~README screenshots and architecture diagram.~~ Done.
3. Automated prevention triggers: notify the responsible role when an alert opens.
4. Unknown or approximate locations reflected in confidence and validation.
5. Regulator/policy summary export.
6. Dashboard and Validation page polish; role checks on every page.
7. Extra privacy tests across all roles and endpoints.

## Later

AI-drafted plain-language alert briefings (clearly labelled); real open-data baselines; Postgres persistence; real authentication with a dedicated regulator role and an audit log.

## Definition of done for v1.0

- [x] Live link works from a fresh browser; README shows it.
- [x] Fresh clone to running app with `npm run setup` and `npm run dev`.
- [x] CI green on `main`; tests lock the headline numbers.
- [ ] No endpoint returns individual records or recoverable small counts.
- [ ] README, PRD and TRD numbers match the back-test.
