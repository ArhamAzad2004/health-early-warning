# Sentinel Dubai — Product Requirements (PRD)

Hackathon entry for the "Population and Workforce Health Early Warning" challenge.
Repo: `health-early-warning`. Stack: Python FastAPI + React (Vite). Data: fully simulated health/work data, plus live Dubai weather and air quality from Open-Meteo.

## 1. Problem

Health risks in a city and its workforce show up in several places before anyone joins the dots: a heat wave in the weather feed, a rise in incident reports on a construction site, more sick days, then a spike in clinic visits. Each signal sits in a different system owned by a different organisation, and the first time anyone acts is after the harm has peaked.

Sentinel Dubai is an early-warning console that fuses population, environmental, service and workplace signals, explains why risk is rising, and recommends a proportionate action to the person whose job it is to take it — early enough to matter, specific enough to use, and calibrated so people do not learn to ignore it.

## 2. Setting (demo world)

- City: Dubai, 8 districts (Deira, Bur Dubai, Al Quoz, Al Qusais, Jebel Ali, Dubai Marina, Business Bay, Dubai Silicon Oasis).
- One large employer: fictional **Gulf Build Co. (GBC)** with three construction sites: Site A – Jebel Ali (1,200 workers), Site B – Al Quoz (800), Site C – Business Bay (600).
- Time window: 1 May 2025 to 30 Sep 2025, daily. Health and work data are synthetic (seed 42) with two injected scenarios as ground truth. Live weather/AQI is real.

## 3. Users

| User | Organisation | What they need |
|---|---|---|
| District Public Health Officer | Dubai health authority | See which districts are heating up, why, and what advisory to issue. |
| Employer HSE Manager | Gulf Build Co. | See only their own sites, aggregated. Act on heat/absence/incident patterns. |
| Occupational Health Inspector | Regulator | Be named on site alerts; see evidence, not individuals. Uses the `public_health` view in the prototype. |
| Public | Residents and outdoor workers | District-level environment and advisories only. No counts, no workplace data. |

## 4. Goals

1. Detect each injected scenario before its harm peak and report the lead time honestly.
2. Every alert explains itself: which signals, which area, which days, how much each contributed.
3. Every alert carries a proportionate action, named responsible roles, evidence and assumptions.
4. Privacy by default: aggregated counts only, small cells suppressed, role-based views, visible boundary against employment or disciplinary use.
5. Validation page a judge can read in one minute: lead time, sensitivity, PPV, false alarms, latency, missing-input re-runs, calibration sweep, impact estimate.

## 5. Non-goals (for the hackathon)

- No real patient or employee data; no database; no login (role switcher instead).
- No causal claims. Alerts say "signals rose together", not "X caused Y".
- No machine-learned model. Detection is transparent statistics (z-scores, EWMA, weighted fusion).
- No LLM in the loop. "Claude-written alert briefings" is a stretch goal only.

## 6. Features

- **F1 Synthetic Dubai simulator** — daily series for 7 signals across 8 districts and 3 sites, fixed seed, generated in memory at startup, with Poisson noise, ~3 % random missing days and one 3-day HR feed outage at Site A during the heat cluster.
- **F2 Injected scenarios** — S1 heat-stress cluster at GBC Site A – Jebel Ali (14–27 Jul, harm peak 23 Jul); S2 dust-storm respiratory spike in Al Quoz and Al Qusais with absence at GBC Site B (21 Aug – 6 Sep, peak 30 Aug).
- **F3 Explainable detection** — per area per signal: rolling 28-day baseline, positive z-score capped at 6, EWMA smoothing; each signal used only as it was known that day (reporting latency); environmental spikes remembered for 7 days as exposure; weighted fusion into one risk score; levels normal / watch 4.5 / warning 6.0 / alert 7.5.
- **F4 Alert fatigue controls** — an alert opens only after 2 consecutive days at risk ≥ 4.5 with ≥ 2 signals corroborating, at least one of them a health or workplace count. Weather alone never alarms. Watch threshold chosen from a calibration sweep.
- **F5 Alert cards** — area, dates, peak risk, level, per-signal contribution shares, evidence (value vs baseline, z, date), action, roles, assumptions, data completeness and confidence.
- **F6 Rule-based playbook** — three branches: site heat pattern, district heat pattern, respiratory/air-quality pattern; each with an urgent and a lower-level wording.
- **F7 Map + timeline** — Leaflet map of Dubai, circles sized and coloured by risk level, date slider to replay the season.
- **F8 Live environment strip** — current Dubai temperature, humidity, feels-like, PM10, PM2.5, US AQI and dust from Open-Meteo, with graceful offline fallback.
- **F9 Privacy & roles** — aggregated counts, "<5" suppression, role switcher (`public_health`, `employer_hse`, `public`), boundary banner, governance panel.
- **F10 Validation page** — back-test metrics, lead time per scenario, five missing-input re-runs, calibration sweep, impact estimate with assumptions.

## 7. How this wins — judging requirements mapped to demo moments

| # | Requirement | Where the judge sees it |
|---|---|---|
| 1 | Multi-signal surveillance (≥2 materially different signal types) | S1 produces alerts at Site A (occupational incidents, administrative absence, environmental heat index) and in Jebel Ali district (clinical heat-illness visits, heat index): four materially different signal types in one event. |
| 2 | Explainable anomaly detection | Contribution shares per signal over the alert window, plus an evidence row per signal: the day, observed value, baseline and z. The area and start/end dates are on the card. |
| 3 | Actionable decision support | Action card: "Enforce midday work-break and hydration protocol at site; move heavy work before 11:00; daily heat-illness check-ins by site medic" — roles: Site HSE Manager (Gulf Build Co.), Occupational Health Inspector (regulator); evidence and assumptions listed. |
| 4 | Privacy-preserving views | Switch to `public`: sites vanish, only advisories remain, Validation returns 403. Switch to `employer_hse`: only GBC sites. Counts under 5 show "<5". Banner: "Not for individual employment or disciplinary use". |
| 5 | Operational validation | Validation page: S1 detected 5 days before harm peak, S2 3 days; sensitivity 1.0; area sensitivity 0.8 (GBC Site B missed — accepted known limit, shown on the Validation page); PPV 0.8; 1 false alarm (Al Quoz heat, late June); median data latency 1 day; re-runs without incidents / absence / aqi / heat_index / lab_resp_pos; calibration sweep 3.0–6.0. |
| 6 | Health and resilience impact | Impact box: excess absence days and incidents at GBC sites after first alert × 30 % intervention effectiveness → avoided lost workdays and avoided high-severity incidents (10 % severity share). Assumptions printed beside the numbers. |

## 8. Demo script (3–5 minutes)

1. **(0:00) Hook.** "Dubai, July 2025. A heat wave is building. Who finds out first — the clinic, or the site?" Open Overview as `public_health`. Live strip shows today's real Dubai temperature and AQI.
2. **(0:30) Replay.** Press play from 1 May. Circles stay calm, then around 18 July GBC Site A – Jebel Ali crosses watch and opens an alert. Point out it did not fire on one noisy day: two days running, two signals, one of them a workplace count.
3. **(1:15) Explain.** Open the Site A alert. Contribution shares and the timeline with baseline band: heat index rose first (exposure memory), then incidents and absence. Open the Jebel Ali district alert: heat-illness clinic visits followed. "Four materially different signals, one story."
4. **(2:00) Act.** Action card: proportionate action, responsible roles, evidence vs baseline, assumptions, completeness and confidence (the Site A HR outage lowers it visibly). "This goes to the Site HSE Manager, not to HR."
5. **(2:45) Protect.** Switch role to `employer_hse` (only GBC sites) then `public` (districts, advisories only). Show a "<5" suppressed cell and the boundary banner.
6. **(3:15) Prove.** Validation page: lead time 5 and 3 days, sensitivity 1.0, PPV 0.8, 1 false alarm, GBC Site B missed (accepted known limit). Missing-input table: how lead time and false alarms move without `incidents` or `aqi`. Calibration sweep shows why watch = 4.5.
7. **(3:50) Impact and close.** Impact estimate with its assumptions on screen. "Earlier, explainable, proportionate, private. Built on open tools, ready for real feeds."

## 9. Success metrics (demo day) and current result

- Both scenarios detected with lead time ≥ 2 days — **current: S1 5 days, S2 3 days.** GBC Site B missed in S2 — **accepted known limit**, surfaced on the Validation page.
- False alarms ≤ 3 across the window — **current: 1.** PPV ≥ 0.7 — **current: 0.8.**
- Every alert has action, roles, evidence, assumptions, completeness and confidence — **true by construction.**
- Role switch changes visible areas within one second; no endpoint ever returns individual records.
- Backend starts in < 5 s; `/api/live` returns within 6 s or returns `ok: false`.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Scenarios too obvious → looks staged | Poisson noise, missing gaps and a feed outage are in the data; false alarm and the missed GBC Site B area are accepted as a known limit and shown honestly on the Validation page. |
| Threshold tuned to the demo only | Calibration sweep and five missing-input re-runs on the Validation page; weights and thresholds printed in every alert's assumptions. |
| Open-Meteo offline during pitch | `/api/live` returns `ok: false`; UI shows "Live feed unavailable" and nothing else breaks. |
| Judges ask "is it real?" | Say up front: synthetic health/work data, real weather; schema designed for real feeds. |
| Alert fatigue critique | Persistence rule, corroboration rule, three severity levels, false-alarm count on screen. |

## 11. Stretch goals (after the core demo works)

Claude-written alert briefings (plain-language paragraph per alert); real open-data baselines replacing synthetic districts; Postgres persistence; real authentication and a dedicated regulator role replacing the role switcher.
