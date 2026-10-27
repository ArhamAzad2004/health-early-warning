"""Explainable multi-signal detection, alerting, decision support and back-test.

Method (per area, per signal): rolling 28-day baseline of previous days -> z-score ->
positive part, capped -> EWMA smoothing. Risk on day D fuses each signal as it was
*known* on day D, i.e. its smoothed z on day D - reporting latency. An alert opens when
risk >= WATCH on two consecutive days with at least two signals corroborating.
"""
import statistics
from .sim import AREAS, DATES, SCENARIOS, SIGNALS

DATE_ISO = [d.isoformat() for d in DATES]

WINDOW, MIN_HISTORY, Z_CAP, ALPHA = 28, 7, 6.0, 0.5
# Environmental exposure alone should not alarm, so it carries less weight than health outcomes.
WEIGHTS = {"resp_visits": 1.0, "heat_visits": 1.0, "lab_resp_pos": 1.0, "absence": 0.8,
           "incidents": 1.0, "heat_index": 0.6, "aqi": 0.6}
WATCH, WARNING, ALERT = 4.5, 6.0, 7.5  # WATCH chosen from the calibration sweep in backtest()
CORROBORATE_Z = 1.5
EXPOSURE_LAG = 7  # days an environmental spike keeps counting as exposure
HEAT_GROUP = {"heat_index", "heat_visits", "incidents"}


def level(risk):
    return "alert" if risk >= ALERT else "warning" if risk >= WARNING else "watch" if risk >= WATCH else "normal"


def area_series(data, a):
    """A site's own workplace signals plus the environment of the district it sits in."""
    s = dict(data[a])
    parent = AREAS[a].get("parent")
    if parent:
        s["heat_index"], s["aqi"] = data[parent]["heat_index"], data[parent]["aqi"]
    return s


def baseline_z(values, is_count):
    """Per day: (baseline mean, z, smoothed z). Missing day -> z None, EWMA fed 0."""
    out, ew = [], 0.0
    for i, v in enumerate(values):
        hist = [x for x in values[max(0, i - WINDOW):i] if x is not None]
        mean = z = None
        if len(hist) >= MIN_HISTORY:
            mean = statistics.fmean(hist)
            sd = statistics.pstdev(hist)
            sd = max(sd, mean ** 0.5 if is_count else 0.5, 1.0 if is_count else 0.5)
            if v is not None:
                z = min(Z_CAP, max(0.0, (v - mean) / sd))
        ew = ALPHA * (z or 0.0) + (1 - ALPHA) * ew
        out.append((None if mean is None else round(mean, 1), None if z is None else round(z, 2), ew))
    return out


def score_area(series, exclude=()):
    """Daily risk with per-signal contributions, respecting each signal's reporting latency."""
    zs = {s: baseline_z(v, SIGNALS[s]["count"]) for s, v in series.items() if s not in exclude}
    days = []
    for i in range(len(DATES)):
        contrib, missing, strong, outcome_strong = {}, [], 0, 0
        for s, rows in zs.items():
            j = i - SIGNALS[s]["latency"]
            if j < 0 or series[s][j] is None:
                missing.append(s)
            if SIGNALS[s]["count"]:
                ew = 0.0 if s in missing else rows[j][2]
            else:  # exposure acts with a lag (dust -> coughs days later), so remember the last week's peak
                ew = max((rows[k][2] for k in range(max(0, j - EXPOSURE_LAG + 1), j + 1)), default=0.0)
            contrib[s] = WEIGHTS[s] * ew
            if ew >= CORROBORATE_Z:
                strong += 1
                outcome_strong += SIGNALS[s]["count"]
        risk = sum(contrib.values())
        # Weather alone never alarms: a health or workplace signal must be one of the corroborators.
        days.append(dict(risk=round(risk, 2), contrib=contrib, missing=missing, strong=strong if outcome_strong else 0))
    return zs, days


def playbook(area_id, shares, lvl):
    a = AREAS[area_id]
    heat = sum(v for s, v in shares.items() if s in HEAT_GROUP) + (shares.get("absence", 0) if a["type"] == "site" else 0) / 2
    resp = 1 - heat
    urgent = lvl in ("warning", "alert")
    if heat >= resp and a["type"] == "site":
        return dict(
            action=("Enforce midday work-break and hydration protocol at site; move heavy work before 11:00; "
                    "daily heat-illness check-ins by site medic" if urgent else
                    "Remind site supervisors of heat protocol; increase water/shade checks; review in 24h"),
            roles=["Site HSE Manager (Gulf Build Co.)", "Occupational Health Inspector (regulator)"],
            category="heat")
    if heat >= resp:
        return dict(
            action=("Issue district heat-health advisory; inspect outdoor worksites for midday-break compliance; "
                    "brief clinics on heat-illness triage" if urgent else
                    "Share heat advisory with district clinics and employers; review in 24h"),
            roles=["District Public Health Officer", "Occupational Health Inspector (regulator)"],
            category="heat")
    return dict(
        action=("Issue district air-quality health advisory; alert clinics and labs to expect respiratory demand; "
                "advise outdoor workers on masks and reduced exertion" if urgent else
                "Notify clinics of rising respiratory activity; monitor AQI and lab positives; review in 24h"),
        roles=["District Public Health Officer", "Site HSE Manager (Gulf Build Co.)" if a["type"] == "site" else "Environmental Health Officer"],
        category="respiratory")


def find_alerts(area_id, series, zs, days, watch=WATCH):
    alerts, run, cur, below = [], 0, None, 0
    for i, d in enumerate(days):
        gate = d["risk"] >= watch and d["strong"] >= 2
        run = run + 1 if gate else 0
        if cur is None and run >= 2:
            cur, below = dict(start=i, end=i), 0
        elif cur is not None:
            below = below + 1 if d["risk"] < watch else 0
            if below >= 2:
                alerts.append(cur)
                cur = None
            else:
                cur["end"] = i
    if cur:
        alerts.append(cur)
    return [_describe(area_id, series, zs, days, a["start"], a["end"]) for a in alerts]


def _describe(area_id, series, zs, days, i0, i1):
    window = days[i0:i1 + 1]
    totals = {s: sum(d["contrib"][s] for d in window) for s in zs}
    total = sum(totals.values()) or 1
    shares = {s: round(v / total, 3) for s, v in sorted(totals.items(), key=lambda kv: -kv[1])}
    peak = max(window, key=lambda d: d["risk"])
    lvl = level(peak["risk"])
    evidence = []
    for s, share in shares.items():
        if share < 0.05:
            continue
        lat = SIGNALS[s]["latency"]
        idx = [i - lat for i in range(i0, i1 + 1) if i - lat >= 0 and series[s][i - lat] is not None]
        if not idx:
            continue
        j = max(idx, key=lambda k: zs[s][k][1] or 0)
        evidence.append(dict(signal=s, label=SIGNALS[s]["label"], date=DATES[j].isoformat(),
                             value=series[s][j], baseline=zs[s][j][0], z=zs[s][j][1], share=share))
    cells = len(window) * len(zs)
    completeness = round(1 - sum(len(d["missing"]) for d in window) / cells, 2)
    return dict(
        id=f"{area_id}-{DATES[i0].isoformat()}", area_id=area_id, area=AREAS[area_id]["name"],
        start=DATES[i0].isoformat(), end=DATES[i1].isoformat(), peak_risk=peak["risk"], level=lvl,
        contributions=shares, evidence=evidence, completeness=completeness,
        confidence="high" if completeness >= 0.9 else "medium" if completeness >= 0.75 else "low",
        **playbook(area_id, shares, lvl),
        assumptions=[
            f"Baseline = previous {WINDOW} days; z-scores capped at {Z_CAP}; EWMA alpha {ALPHA}.",
            f"Weights: health outcomes 1.0, absence 0.8, environment 0.6 (exposure alone does not alarm).",
            f"Opens when risk >= {WATCH} two days running with >= 2 signals at smoothed z >= {CORROBORATE_Z}.",
            "Each signal is used only as it was known that day (reporting latency respected).",
            "Missing data contributes 0 and lowers confidence; data are synthetic.",
        ])


def run(data, exclude=(), watch=WATCH):
    scores, alerts = {}, []
    for a in AREAS:
        series = area_series(data, a)
        zs, days = score_area(series, exclude)
        scores[a] = dict(series=series, zs=zs, days=days)
        alerts += find_alerts(a, series, zs, days, watch)
    alerts.sort(key=lambda x: x["start"])
    return scores, alerts


def _metrics(alerts):
    def hits(al, sc):
        return al["area_id"] in sc["areas"] and al["start"] <= sc["end"].isoformat() and al["end"] >= sc["start"].isoformat()
    per = []
    for sc in SCENARIOS:
        tp = [al for al in alerts if hits(al, sc)]
        first = min((al["start"] for al in tp), default=None)
        lead = (sc["peak"] - DATES[DATE_ISO.index(first)]).days if first else None
        per.append(dict(id=sc["id"], name=sc["name"], peak=sc["peak"].isoformat(), detected=bool(tp),
                        first_alert=first, lead_time_days=lead, areas_hit=sorted({al["area_id"] for al in tp}),
                        areas_affected=sc["areas"]))
    true_alerts = [al for al in alerts if any(hits(al, sc) for sc in SCENARIOS)]
    pairs = sum(len(sc["areas"]) for sc in SCENARIOS)
    leads = [p["lead_time_days"] for p in per if p["lead_time_days"] is not None]
    return dict(
        scenarios=per,
        sensitivity=round(sum(p["detected"] for p in per) / len(per), 2),
        area_sensitivity=round(sum(len(p["areas_hit"]) for p in per) / pairs, 2),
        ppv=round(len(true_alerts) / len(alerts), 2) if alerts else None,
        false_alarms=len(alerts) - len(true_alerts),
        total_alerts=len(alerts),
        mean_lead_time_days=round(statistics.fmean(leads), 1) if leads else None)


def backtest(data, alerts):
    base = _metrics(alerts)
    base["data_latency_days"] = {s: SIGNALS[s]["latency"] for s in SIGNALS}
    base["median_latency_days"] = statistics.median(SIGNALS[s]["latency"] for s in SIGNALS)
    base["missing_input"] = []
    for s in ("incidents", "absence", "aqi", "heat_index", "lab_resp_pos"):
        m = _metrics(run(data, exclude=(s,))[1])
        base["missing_input"].append(dict(without=s, label=SIGNALS[s]["label"], **{
            k: m[k] for k in ("sensitivity", "area_sensitivity", "ppv", "false_alarms", "mean_lead_time_days")}))
    base["calibration"] = [dict(threshold=t, **{k: m[k] for k in ("sensitivity", "ppv", "false_alarms", "mean_lead_time_days")})
                           for t in (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0) for m in [_metrics(run(data, watch=t)[1])]]
    # Impact: clearly labelled assumptions, not a claim.
    eff, sev_share = 0.3, 0.1
    excess = {"absence": 0.0, "incidents": 0.0}
    for sc, p in zip(SCENARIOS, base["scenarios"]):
        if not p["first_alert"]:
            continue
        i0, i1 = DATE_ISO.index(p["first_alert"]), DATE_ISO.index(sc["end"].isoformat())
        for a in sc["areas"]:
            for s in excess if AREAS[a]["type"] == "site" else ():
                zs = baseline_z(data[a][s], True)
                excess[s] += sum(max(0, (data[a][s][i] or 0) - (zs[i][0] or 0)) for i in range(i0, i1 + 1))
    base["impact"] = dict(
        assumptions=[f"Acting at the first alert prevents {int(eff * 100)}% of the excess harm that followed it.",
                     f"{int(sev_share * 100)}% of excess heat/exertion incidents would have been high-severity.",
                     "Excess = observed minus rolling baseline at affected GBC sites, from first alert to scenario end."],
        excess_absence_days=round(excess["absence"]), avoided_lost_workdays=round(excess["absence"] * eff),
        excess_incidents=round(excess["incidents"]), avoided_incidents=round(excess["incidents"] * eff, 1),
        avoided_high_severity_incidents=round(excess["incidents"] * eff * sev_share, 1))
    return base
