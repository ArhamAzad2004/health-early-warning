# Sentinel Dubai — health early warning (hackathon)

Prototype that fuses simulated Dubai health, workforce and environmental signals into explainable, privacy-preserving alerts. Plan and requirements live in `docs/` (PRD, TRD, APP_FLOW, DESIGN_BRIEF, BACKEND_SCHEMA, IMPLEMENTATION_PLAN); keep them in step with the code when behaviour changes.

## Rules
- Never mention Claude or Claude Code in commits, PR descriptions, code, comments or docs. No `Co-Authored-By` trailer, no "Generated with" line.
- A working demo beats breadth. Prefer small changes that keep the demo path working: map → Play → click alert → Validation tab.
- Privacy is a judged requirement: never add an endpoint or field that returns individual-level data; health/work counts 1–4 must stay suppressed (`suppress()` in `backend/app/main.py`) — including inside alert evidence.
- Health/workforce data are synthetic; don't present numbers as real-world findings.

## Run
- Backend (from `backend/`): `.venv/Scripts/python -m uvicorn app.main:app --port 8000` (first time: `python -m venv .venv` then `.venv/Scripts/python -m pip install -r requirements.txt`)
- Frontend (from `frontend/`): `npm install` once, then `npm run dev` → http://localhost:5173 (Vite proxies `/api` to port 8000)
- Tests (from `backend/`): `.venv/Scripts/python -m pytest -q` — must pass before committing.
- Windows machine: PowerShell and Git Bash both available.

## Code map
- `backend/app/sim.py` — areas (8 districts, 3 Gulf Build Co. sites), 7 signals with reporting latency, 2 injected scenarios (S1 heat cluster Jebel Ali, S2 dust storm), seeded generator. Data is generated in memory at startup; no database.
- `backend/app/engine.py` — 28-day baseline z-scores → EWMA → weighted fused risk (latency respected, 7-day exposure memory for weather), alert gating (2 days, ≥2 signals, ≥1 health/work signal), playbook, back-test (`calibration`, `missing_input`, `impact`).
- `backend/app/main.py` — FastAPI: `/api/meta, areas, signals, risk, alerts, backtest, live`; every endpoint takes `?role=public_health|employer_hse|public`.
- `frontend/src/` — React + Vite, Leaflet map, Recharts. `App.jsx` (shell, role switcher, live strip), `Overview.jsx`, `AlertDetail.jsx`, `Validation.jsx`, `Privacy.jsx`, `styles.css`.

## Tuning
- Thresholds and weights are constants at the top of `engine.py`. If you change them, re-run the back-test and update the numbers quoted in `README.md`, `docs/PRD.md` and `docs/TRD.md`.
- Current back-test: both scenarios detected, lead 5 d (S1) / 3 d (S2), PPV 0.8, 1 false alarm. Known limit (accepted): GBC Site B missed in S2 (absence-only workplace signal in the dust event did not corroborate on two consecutive days) — surfaced on the Validation page as a known limit; AQI picks up ~12% share in the Site A heat alert.
- Design: colour-blind-safe level colours (`frontend/src/api.js`) always paired with text labels; see `docs/DESIGN_BRIEF.md`.
