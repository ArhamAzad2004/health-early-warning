# Sentinel Dubai — Backend Schema and API

**Prototype note.** The backend keeps everything in memory, generated with seed 42 at startup (`sim.generate()`), scored once (`engine.run()`) and back-tested once (`engine.backtest()`). The tables below describe the same entities as they would be in Postgres later; today they are Python dicts and lists with the field names shown. Nothing here ever holds an individual-level record.

## 1. Entities

### `area` (`sim.AREAS`)
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | `deira`, `bur_dubai`, `al_quoz`, `al_qusais`, `jebel_ali`, `dubai_marina`, `business_bay`, `silicon_oasis`, `gbc_site_a`, `gbc_site_b`, `gbc_site_c` |
| `name` | text | e.g. "GBC Site A – Jebel Ali" |
| `type` | text | `district` or `site` |
| `lat`, `lon` | float | districts: Deira 25.271/55.307, Bur Dubai 25.254/55.290, Al Quoz 25.136/55.232, Al Qusais 25.277/55.376, Jebel Ali 25.005/55.110, Dubai Marina 25.080/55.140, Business Bay 25.186/55.262, Silicon Oasis 25.118/55.390; sites: A 25.020/55.125, B 25.145/55.245, C 25.190/55.270 |
| `size` | float, districts only | relative population scale (0.6–1.2) |
| `workers` | int, sites only | A 1200, B 800, C 600 |
| `parent` | text FK → area.id, sites only | A → `jebel_ali`, B → `al_quoz`, C → `business_bay` |

### `signal_def` (`sim.SIGNALS`)
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | `resp_visits`, `heat_visits`, `lab_resp_pos`, `absence`, `incidents`, `heat_index`, `aqi` |
| `label` | text | "Respiratory clinic visits", "Heat-illness clinic visits", "Lab respiratory positives", "Sickness-absence days", "Heat/exertion incident reports", "Heat index (°C)", "Air quality index (PM10)" |
| `kind` | text | `service`, `service`, `laboratory`, `workplace`, `occupational`, `environmental`, `environmental` |
| `level` | text | `district` or `site` |
| `latency` | int (days) | 1, 1, 3, 2, 1, 0, 0 |
| `count` | bool | true for the five health/workplace signals; drives suppression and the sd floor |

Fusion weights live in `engine.WEIGHTS` (1.0 for all counts except `absence` 0.8; 0.6 for both environmental).

### `observation` (`DATA[area_id][signal_id][day_index]`)
| Field | Type | Notes |
|---|---|---|
| `area_id`, `signal_id` | FK | sites hold only `absence`, `incidents`; districts hold the other five |
| `date` | date | 2025-05-01 … 2025-09-30 (index 0 … 152) |
| `value` | float, nullable | null = missing (≈3 % random, plus Site A `absence` 20–22 Jul) |

`reported_on = date + latency` is derived, not stored.

### `score` (`SCORES[area_id]`)
Per signal per day a tuple `(baseline, z, ewma)`: `baseline` rolling mean of previous 28 days (null until 7 values exist), `z` positive capped at 6 (null when missing), `ewma` smoothed z. Per day: `risk`, `contrib` (signal → weight × ewma as known that day), `missing` (list of signals not known that day), `strong` (count of corroborating signals, 0 if none is a count signal).

### `alert` (`ALERTS`)
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | `{area_id}-{start}`, e.g. `gbc_site_a-2025-07-18` |
| `area_id` | FK | |
| `area` | text | area name |
| `start`, `end` | date | opens on 2nd consecutive gated day; closes after 2 days below 4.5 |
| `peak_risk` | float | |
| `level` | text | `watch`, `warning` or `alert` (level of the peak day) |
| `contributions` | json | `{signal_id: share}` sorted descending, shares sum to 1 over the window |
| `evidence` | json[] | `{signal, label, date, value, baseline, z, share}` for signals with share ≥ 0.05 |
| `completeness` | float 0–1 | 1 − missing cells / (days × signals) |
| `confidence` | text | `high` ≥ 0.90, `medium` ≥ 0.75, else `low` |
| `action` | text | from playbook |
| `roles` | text[] | responsible first, then notified |
| `category` | text | `heat` or `respiratory` |
| `assumptions` | text[] | five sentences: window/cap/alpha; weights; opening rule; latency; missing + synthetic |

### `alert_contribution` (future table; today the `contributions` dict and `evidence` list above)
`alert_id, signal_id, share, evidence_date, evidence_value, evidence_baseline, evidence_z`.

### `scenario` (`sim.SCENARIOS`, ground truth)
| id | name | start | end | peak | areas |
|---|---|---|---|---|---|
| S1 | Heat-stress cluster at GBC Site A – Jebel Ali | 2025-07-14 | 2025-07-27 | 2025-07-23 | `gbc_site_a`, `jebel_ali` |
| S2 | Dust storm respiratory spike (Al Quoz, Al Qusais) | 2025-08-21 | 2025-09-06 | 2025-08-30 | `al_quoz`, `al_qusais`, `gbc_site_b` |

### `role_permission` (`main.visible` + per-endpoint rules)
| Role | Areas | `/api/signals` | `/api/alerts` | `/api/backtest` |
|---|---|---|---|---|
| `public_health` | all | all signals | full | full |
| `employer_hse` | `type == site` | all site signals (incl. parent env) | full | full |
| `public` | `type == district` | `heat_index`, `aqi` only | `id, area_id, area, start, end, level, action, category` | 403 |

### `audit_log` (future, not in prototype)
`id, timestamp, role, endpoint, params, areas_returned` — who viewed what, to support the governance boundary.

## 2. Suppression rule (`main.suppress`)

Applied to every count signal in `/api/signals` and to `evidence[].value` in `/api/alerts`:
- value 0 → `value: 0, suppressed: false`
- value 1–4 → `value: null, suppressed: true` (UI shows "<5")
- value ≥ 5 → `value: v, suppressed: false`
- missing → `value: null, suppressed: false, missing: true`
`heat_index` and `aqi` are never suppressed. `baseline` and `z` are still returned.

## 3. API

All endpoints are `GET`, JSON. All except `/api/meta` and `/api/live` accept `?role=public_health|employer_hse|public` (default `public_health`; anything else → 422). Example values below are illustrative; the seeded run is the source of truth.

### `GET /api/meta`
```json
{"start": "2025-05-01", "end": "2025-09-30",
 "signals": {"incidents": {"label": "Heat/exertion incident reports", "kind": "occupational", "level": "site", "latency": 1, "count": true}},
 "levels": {"watch": 4.5, "warning": 6.0, "alert": 7.5}}
```

### `GET /api/areas?role=employer_hse`
```json
[{"id": "gbc_site_a", "name": "GBC Site A – Jebel Ali", "type": "site", "lat": 25.02, "lon": 55.125, "workers": 1200, "parent": "jebel_ali"}]
```
Districts carry `size` instead of `workers`/`parent`.

### `GET /api/signals?area_id=gbc_site_a&role=employer_hse`
```json
{"area_id": "gbc_site_a",
 "signals": {
   "incidents": [
     {"date": "2025-07-16", "value": 7, "suppressed": false, "missing": false, "baseline": 1.9, "z": 3.6},
     {"date": "2025-07-17", "value": null, "suppressed": true, "missing": false, "baseline": 2.0, "z": 1.4},
     {"date": "2025-07-21", "value": null, "suppressed": false, "missing": true, "baseline": 2.3, "z": null}],
   "absence": [], "heat_index": [], "aqi": []},
 "risk": [{"date": "2025-07-18", "risk": 5.1, "level": "watch"}]}
```
Out-of-scope or unknown `area_id` → `404 "Area not visible for this role"`.

### `GET /api/risk?date=2025-07-20&role=public_health`
```json
[{"area_id": "gbc_site_a", "risk": 6.4, "level": "warning", "missing": ["absence"]},
 {"area_id": "deira", "risk": 0.8, "level": "normal", "missing": []}]
```
Date outside the window → 400.

### `GET /api/alerts?role=public_health`
```json
[{"id": "gbc_site_a-2025-07-18", "area_id": "gbc_site_a", "area": "GBC Site A – Jebel Ali",
  "start": "2025-07-18", "end": "2025-07-28", "peak_risk": 7.9, "level": "alert",
  "contributions": {"incidents": 0.42, "heat_index": 0.27, "absence": 0.24, "aqi": 0.07},
  "evidence": [{"signal": "incidents", "label": "Heat/exertion incident reports", "date": "2025-07-20", "value": 9, "baseline": 2.1, "z": 4.6, "share": 0.42}],
  "completeness": 0.86, "confidence": "medium",
  "action": "Enforce midday work-break and hydration protocol at site; move heavy work before 11:00; daily heat-illness check-ins by site medic",
  "roles": ["Site HSE Manager (Gulf Build Co.)", "Occupational Health Inspector (regulator)"],
  "category": "heat",
  "assumptions": ["Baseline = previous 28 days; z-scores capped at 6.0; EWMA alpha 0.5.",
                  "Weights: health outcomes 1.0, absence 0.8, environment 0.6 (exposure alone does not alarm).",
                  "Opens when risk >= 4.5 two days running with >= 2 signals at smoothed z >= 1.5.",
                  "Each signal is used only as it was known that day (reporting latency respected).",
                  "Missing data contributes 0 and lowers confidence; data are synthetic."]}]
```
With `role=public` each object is trimmed to `id, area_id, area, start, end, level, action, category`.

### `GET /api/backtest?role=public_health`
```json
{"scenarios": [
   {"id": "S1", "name": "Heat-stress cluster at GBC Site A – Jebel Ali", "peak": "2025-07-23", "detected": true,
    "first_alert": "2025-07-18", "lead_time_days": 5, "areas_hit": ["gbc_site_a", "jebel_ali"], "areas_affected": ["gbc_site_a", "jebel_ali"]},
   {"id": "S2", "name": "Dust storm respiratory spike (Al Quoz, Al Qusais)", "peak": "2025-08-30", "detected": true,
    "first_alert": "2025-08-27", "lead_time_days": 3, "areas_hit": ["al_quoz", "al_qusais"], "areas_affected": ["al_quoz", "al_qusais", "gbc_site_b"]}],
 "sensitivity": 1.0, "area_sensitivity": 0.8, "ppv": 0.8, "false_alarms": 1, "total_alerts": 5, "mean_lead_time_days": 4.0,
 "data_latency_days": {"resp_visits": 1, "heat_visits": 1, "lab_resp_pos": 3, "absence": 2, "incidents": 1, "heat_index": 0, "aqi": 0},
 "median_latency_days": 1,
 "missing_input": [{"without": "incidents", "label": "Heat/exertion incident reports", "sensitivity": 1.0, "area_sensitivity": 0.6, "ppv": 0.75, "false_alarms": 1, "mean_lead_time_days": 3.0}],
 "calibration": [{"threshold": 4.5, "sensitivity": 1.0, "ppv": 0.8, "false_alarms": 1, "mean_lead_time_days": 4.0}],
 "impact": {"assumptions": ["Acting at the first alert prevents 30% of the excess harm that followed it.",
                            "10% of excess heat/exertion incidents would have been high-severity.",
                            "Excess = observed minus rolling baseline at affected GBC sites, from first alert to scenario end."],
            "excess_absence_days": 120, "avoided_lost_workdays": 36,
            "excess_incidents": 24, "avoided_incidents": 7.2, "avoided_high_severity_incidents": 0.7}}
```
`missing_input` has five rows (`incidents`, `absence`, `aqi`, `heat_index`, `lab_resp_pos`); `calibration` has seven (3.0 … 6.0). `role=public` → 403.

### `GET /api/live`
```json
{"ok": true, "time": "2026-10-27T13:00", "temperature": 34.1, "humidity": 58, "feels_like": 39.6,
 "pm10": 71.0, "pm2_5": 28.4, "us_aqi": 62, "dust": 12.0, "source": "Open-Meteo"}
```
On failure (6 s timeout or any error): `{"ok": false, "error": "...", "fetched": "2026-10-27"}`.
