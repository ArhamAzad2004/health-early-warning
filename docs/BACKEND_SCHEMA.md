# Sentinel Dubai — Backend Schema and API

**Prototype note.** The hackathon backend keeps everything in memory, generated with a fixed seed at startup. The tables below describe the same entities as they would be in Postgres later; today they are Python lists/dicts (or pandas frames) with the same field names. Nothing here ever holds an individual-level record.

## 1. Entities

### `area`
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | slug, e.g. `jebel_ali`, `gbc_site_a` |
| `name` | text | e.g. "GBC Site A – Jebel Ali" |
| `type` | text | `district` or `site` |
| `lat`, `lon` | float | centroid |
| `parent_district` | text FK → area.id, nullable | sites only |
| `employer` | text, nullable | `Gulf Build Co.` for sites |

Districts: Deira, Bur Dubai, Al Quoz, Al Qusais, Jebel Ali, Dubai Marina, Business Bay, Dubai Silicon Oasis. Sites: GBC Site A – Jebel Ali, GBC Site B – Al Quoz, GBC Site C – Business Bay.

### `signal_def`
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | `resp_visits`, `heat_visits`, `lab_resp_pos`, `absence`, `incidents`, `heat_index`, `aqi` |
| `name` | text | plain label, e.g. "Respiratory clinic visits" |
| `source_type` | text | `service_clinical`, `laboratory`, `workplace_administrative`, `workplace_occupational`, `environmental` |
| `level` | text | `district` or `site` |
| `unit` | text | `count`, `days`, `°C`, `AQI` |
| `latency_days` | int | 1, 1, 3, 2, 1, 0, 0 respectively |
| `weight` | float | fusion weight (assumption) |
| `suppressible` | bool | true for counts, false for environmental |

### `observation`
One row per area per signal per day. The raw simulated value, before suppression.
| Field | Type | Notes |
|---|---|---|
| `area_id` | FK | |
| `signal_id` | FK | |
| `date` | date | 2025-05-01 … 2025-09-30 |
| `value` | float, nullable | null = missing (simulated gap) |
| `reported_on` | date | `date + latency_days`; used by back-test replay |

### `score` (baseline + risk, per area per signal per day)
| Field | Type | Notes |
|---|---|---|
| `area_id`, `signal_id`, `date` | PK | |
| `baseline_mean`, `baseline_std` | float, nullable | rolling 28 prior days |
| `z` | float | positive, capped at 5; 0 if missing |
| `ewma` | float | smoothed z |
| `missing` | bool | |

Plus `area_risk` per area per day: `risk` (float), `level` (`none`/`watch`/`warning`/`alert`), `n_signals_present`, `n_signals_expected`.

### `alert`
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | e.g. `A-0003` |
| `area_id` | FK | |
| `start_date`, `end_date` | date | persistence rule: opens on 2nd consecutive day ≥ 2.0 |
| `peak_date` | date | |
| `peak_risk` | float | |
| `level` | text | highest level reached |
| `pattern` | text | playbook key, e.g. `site_heat`, `district_air_resp` |
| `action` | text | |
| `responsible_role` | text | |
| `notify_roles` | text[] | |
| `evidence` | json[] | `{signal_id, observed, baseline_mean, z, date}` |
| `assumptions` | text[] | |
| `completeness_pct` | float | present / expected signal-days in window |
| `confidence` | text | `high` ≥ 90, `medium` ≥ 70, else `low` |

### `alert_contribution`
| Field | Type |
|---|---|
| `alert_id` | FK |
| `signal_id` | FK |
| `share` | float (0–1, sums to 1 across present signals) |
| `contributing_days` | date[] |
| `missing` | bool |

### `scenario` (ground truth)
| Field | Type | Notes |
|---|---|---|
| `id` | text | `S1`, `S2` |
| `name` | text | "Heat-stress cluster at GBC Site A – Jebel Ali", "Dust storm respiratory spike" |
| `area_ids` | text[] | S1: `gbc_site_a`, `jebel_ali`; S2: `al_quoz`, `al_qusais`, `gbc_site_b` |
| `window_start`, `window_end` | date | |
| `harm_peak_date` | date | used for lead time |

### `role_permission`
| Role | Area types | Signals | Counts shown |
|---|---|---|---|
| `public_health` | district, site | all | aggregated, suppressed |
| `employer_hse` | site (employer = Gulf Build Co.) | absence, incidents, heat_index, aqi | aggregated, suppressed |
| `public` | district | heat_index, aqi | advisories only |

### `audit_log` (future, not in prototype)
`id, timestamp, role, endpoint, params, areas_returned` — would record who viewed what, to support the governance boundary.

## 2. Suppression rule

Applied in the API layer to every count-type signal before the response is built:
- value 0 → `value: 0, suppressed: false`
- value 1–4 → `value: null, suppressed: true` (UI shows "<5")
- value ≥ 5 → `value: v, suppressed: false`
- missing → `value: null, suppressed: false, missing: true`
Environmental signals (`heat_index`, `aqi`) are never suppressed. Baseline and z are still returned so the chart stays explainable without revealing the small count.

## 3. API

All endpoints are JSON, `GET`, and accept `?role=public_health|employer_hse|public` (default `public_health`). An area outside the role's scope returns `404`.

### `GET /api/areas?role=employer_hse`
```json
[
  {"id": "gbc_site_a", "name": "GBC Site A – Jebel Ali", "type": "site",
   "lat": 25.01, "lon": 55.07, "parent_district": "jebel_ali", "employer": "Gulf Build Co."}
]
```

### `GET /api/signals?area_id=al_quoz&role=public_health`
```json
{
  "area_id": "al_quoz",
  "signals": {
    "resp_visits": {
      "name": "Respiratory clinic visits", "unit": "count", "latency_days": 1,
      "series": [
        {"date": "2025-08-24", "value": 12, "suppressed": false, "missing": false, "baseline": 7.9, "z": 1.4},
        {"date": "2025-08-25", "value": null, "suppressed": true, "missing": false, "baseline": 8.0, "z": 0.0},
        {"date": "2025-08-26", "value": null, "suppressed": false, "missing": true, "baseline": 8.1, "z": 0.0}
      ]
    }
  }
}
```

### `GET /api/risk?date=2025-07-18&role=public_health`
```json
{
  "date": "2025-07-18",
  "areas": [
    {"area_id": "gbc_site_a", "risk": 6.8, "level": "alert",
     "top_signals": ["incidents", "absence", "heat_index"], "completeness_pct": 93}
  ]
}
```

### `GET /api/alerts?role=public_health`
```json
[
  {
    "id": "A-0001", "area_id": "gbc_site_a", "area_name": "GBC Site A – Jebel Ali",
    "start_date": "2025-07-15", "end_date": "2025-07-23", "peak_date": "2025-07-18",
    "peak_risk": 6.8, "level": "alert", "pattern": "site_heat",
    "contributions": [
      {"signal_id": "incidents", "share": 0.41, "contributing_days": ["2025-07-14", "2025-07-15", "2025-07-16"], "missing": false},
      {"signal_id": "absence", "share": 0.29, "contributing_days": ["2025-07-15", "2025-07-16"], "missing": false},
      {"signal_id": "heat_index", "share": 0.22, "contributing_days": ["2025-07-12", "2025-07-13", "2025-07-14"], "missing": false},
      {"signal_id": "aqi", "share": 0.0, "contributing_days": [], "missing": true}
    ],
    "action": "Enforce midday work-break and hydration protocol at site; move heavy work to before 11:00",
    "responsible_role": "Site HSE Manager (employer)",
    "notify_roles": ["Occupational Health Inspector (regulator)"],
    "evidence": [
      {"signal_id": "incidents", "date": "2025-07-16", "observed": 9, "baseline_mean": 2.1, "z": 4.6}
    ],
    "assumptions": [
      "Weights: incidents 1.2, absence 0.8, heat_index 0.6, heat_visits 1.0",
      "Alert threshold 2.0 on 2 consecutive days",
      "Synthetic data; reporting latency absence 2d, incidents 1d, heat_index 0d"
    ],
    "completeness_pct": 93, "confidence": "high"
  }
]
```

### `GET /api/backtest`
```json
{
  "scenarios": [
    {"id": "S1", "name": "Heat-stress cluster at GBC Site A – Jebel Ali", "harm_peak_date": "2025-07-20",
     "detection_date": "2025-07-15", "lead_time_days": 5, "detected": true}
  ],
  "overall": {"sensitivity": 1.0, "ppv": 0.67, "false_alarms": 1, "total_alerts": 3, "median_latency_days": 1},
  "missing_input": [
    {"removed": null, "sensitivity": 1.0, "ppv": 0.67, "false_alarms": 1, "lead_time_days": {"S1": 5, "S2": 3}},
    {"removed": "incidents", "sensitivity": 1.0, "ppv": 0.5, "false_alarms": 1, "lead_time_days": {"S1": 2, "S2": 3}},
    {"removed": "aqi", "sensitivity": 1.0, "ppv": 0.67, "false_alarms": 1, "lead_time_days": {"S1": 5, "S2": 1}}
  ],
  "impact": {
    "assumptions": {"intervention_effectiveness": 0.3, "requires_lead_time_days": 1},
    "excess_lost_workdays": 84, "avoided_lost_workdays": 25,
    "excess_high_severity_incidents": 11, "avoided_high_severity_incidents": 3
  }
}
```
Numbers are illustrative; the live values come from the seeded run.

### `GET /api/live`
```json
{"available": true, "fetched_at": "2026-10-27T09:12:00Z", "location": "Dubai",
 "temperature_c": 34.1, "humidity_pct": 58, "apparent_temperature_c": 39.6, "pm10": 71.0, "us_aqi": 62}
```
On failure: `{"available": false, "error": "timeout"}`.
