# Sentinel Dubai — population & workforce health early warning

Hackathon prototype for the **Population and Workforce Health Early Warning** challenge.
It fuses clinic visits, lab positives, sickness absence, occupational incident reports, heat index and air quality
for Dubai districts and a (fictional) construction employer, Gulf Build Co., and raises **explainable,
privacy-preserving alerts** that name a proportionate action and who should take it.

Health and workforce data are **simulated** (fixed seed, two injected outbreaks). Live Dubai weather and air
quality come from [Open-Meteo](https://open-meteo.com) (free, no key).

## What the demo shows

| Challenge requirement | Where to see it |
|---|---|
| 1. Multi-signal surveillance | 7 signals of 5 kinds (service, lab, workplace, occupational, environmental) on the map |
| 2. Explainable detection | Alert page: contribution bars, risk timeline, each signal against its own baseline |
| 3. Decision support | Alert page: recommended action, responsible roles, evidence table, assumptions |
| 4. Privacy | Banner, `<5` suppression, role switcher (public health / employer HSE / public) |
| 5. Validation | Validation tab: lead time, detection, PPV, false alarms, latency, threshold calibration, missing-feed test |
| 6. Impact | Validation tab: estimated lost workdays and incidents avoided, with stated assumptions |

Current back-test: both outbreaks caught **3–5 days before their harm peak**, PPV 80%, 1 false alarm in 5 months across 11 areas.

## Run it locally

Needs Python 3.11+ and Node 20+.

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, press **Play** on the timeline, then click an alert.

Tests: `cd backend && .venv/Scripts/python -m pytest -q`

## Deploy (one public link)

The `Dockerfile` builds the dashboard and serves it from the API, so the whole demo is one app.
On [Render](https://render.com): **New → Blueprint**, pick this repo, and it reads `render.yaml`
(free plan, redeploys on every merge to `main`). Locally, `npm run build` in `frontend/` then start
the backend and open http://localhost:8000.

## Layout

- `backend/app/sim.py` — synthetic Dubai districts, work sites, signals and injected scenarios
- `backend/app/engine.py` — baselines, z-scores, fused risk, alerts, playbook, back-test
- `backend/app/main.py` — FastAPI endpoints with role filtering and small-cell suppression
- `frontend/src/` — React dashboard (Leaflet map, Recharts charts)
- `docs/` — PRD, TRD, app flow, design brief, backend schema, implementation plan
