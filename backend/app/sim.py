"""Synthetic Dubai city + workforce simulator with injected outbreak scenarios.

Everything is aggregated daily counts per area. No individual records exist anywhere.
"""
import math
import random
from datetime import date, timedelta

START, END = date(2025, 5, 1), date(2025, 9, 30)
DATES = [START + timedelta(d) for d in range((END - START).days + 1)]
SEED = 42

# id -> name, type, lat, lon, population (districts) or workers (sites), parent district
AREAS = {
    "deira": dict(name="Deira", type="district", lat=25.271, lon=55.307, size=1.2),
    "bur_dubai": dict(name="Bur Dubai", type="district", lat=25.254, lon=55.290, size=1.0),
    "al_quoz": dict(name="Al Quoz", type="district", lat=25.136, lon=55.232, size=0.9),
    "al_qusais": dict(name="Al Qusais", type="district", lat=25.277, lon=55.376, size=1.0),
    "jebel_ali": dict(name="Jebel Ali", type="district", lat=25.005, lon=55.110, size=0.8),
    "dubai_marina": dict(name="Dubai Marina", type="district", lat=25.080, lon=55.140, size=0.8),
    "business_bay": dict(name="Business Bay", type="district", lat=25.186, lon=55.262, size=0.7),
    "silicon_oasis": dict(name="Dubai Silicon Oasis", type="district", lat=25.118, lon=55.390, size=0.6),
    "gbc_site_a": dict(name="GBC Site A – Jebel Ali", type="site", lat=25.020, lon=55.125, workers=1200, parent="jebel_ali"),
    "gbc_site_b": dict(name="GBC Site B – Al Quoz", type="site", lat=25.145, lon=55.245, workers=800, parent="al_quoz"),
    "gbc_site_c": dict(name="GBC Site C – Business Bay", type="site", lat=25.190, lon=55.270, workers=600, parent="business_bay"),
}

SIGNALS = {
    "resp_visits": dict(label="Respiratory clinic visits", kind="service", level="district", latency=1, count=True),
    "heat_visits": dict(label="Heat-illness clinic visits", kind="service", level="district", latency=1, count=True),
    "lab_resp_pos": dict(label="Lab respiratory positives", kind="laboratory", level="district", latency=3, count=True),
    "absence": dict(label="Sickness-absence days", kind="workplace", level="site", latency=2, count=True),
    "incidents": dict(label="Heat/exertion incident reports", kind="occupational", level="site", latency=1, count=True),
    "heat_index": dict(label="Heat index (°C)", kind="environmental", level="district", latency=0, count=False),
    "aqi": dict(label="Air quality index (PM10)", kind="environmental", level="district", latency=0, count=False),
}

SCENARIOS = [
    dict(id="S1", name="Heat-stress cluster at GBC Site A – Jebel Ali",
         start=date(2025, 7, 14), end=date(2025, 7, 27), peak=date(2025, 7, 23),
         areas=["gbc_site_a", "jebel_ali"]),
    dict(id="S2", name="Dust storm respiratory spike (Al Quoz, Al Qusais)",
         start=date(2025, 8, 21), end=date(2025, 9, 6), peak=date(2025, 8, 30),
         areas=["al_quoz", "al_qusais", "gbc_site_b"]),
]


def _poisson(rng, lam):
    if lam > 30:  # normal approximation is fine for large counts
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


def _ramp(d, start, peak, end):
    """0 outside [start, end], rising to 1 at peak, falling back to 0 at end."""
    if d < start or d > end:
        return 0.0
    if d <= peak:
        return (d - start).days / max(1, (peak - start).days)
    return 1 - (d - peak).days / max(1, (end - peak).days)


def generate(seed=SEED):
    """Returns {area_id: {signal: [value or None per DATES]}}."""
    rng = random.Random(seed)
    data = {a: {} for a in AREAS}
    env = {}
    for a, info in AREAS.items():
        if info["type"] != "district":
            continue
        hi, aqi = [], []
        for i, d in enumerate(DATES):
            season = 38 + 8 * math.sin(math.pi * i / len(DATES))  # peaks mid-summer
            inland = 1.5 if a in ("jebel_ali", "al_quoz") else 0
            h = season + inland + rng.gauss(0, 1.0)
            h += 6 * _ramp(d, date(2025, 7, 13), date(2025, 7, 19), date(2025, 7, 25)) if a in ("jebel_ali", "dubai_marina") else 0
            q = 70 + (15 if a == "al_quoz" else 0) + rng.gauss(0, 8)
            q += 180 * _ramp(d, date(2025, 8, 21), date(2025, 8, 23), date(2025, 8, 26)) if a in ("al_quoz", "al_qusais") else 0
            hi.append(round(h, 1))
            aqi.append(round(max(10, q)))
        env[a] = (hi, aqi)
        data[a]["heat_index"], data[a]["aqi"] = hi, aqi

    s1, s2 = SCENARIOS
    for a, info in AREAS.items():
        if info["type"] == "district":
            hi, aqi = env[a]
            sz = info["size"]
            resp, heat, lab = [], [], []
            for i, d in enumerate(DATES):
                dust = _ramp(d, date(2025, 8, 23), s2["peak"], s2["end"]) if a in s2["areas"] else 0
                heatwave = _ramp(d, date(2025, 7, 17), s1["peak"], s1["end"]) if a in s1["areas"] else 0
                r = _poisson(rng, sz * (22 + 0.04 * (aqi[i] - 70)) * (1 + 2.0 * dust))
                resp.append(r)
                heat.append(_poisson(rng, sz * (2 + 0.5 * max(0, hi[i] - 42)) * (1 + 2.5 * heatwave)))
                lab_dust = _ramp(d, date(2025, 8, 25), date(2025, 9, 1), s2["end"]) if a in s2["areas"] else 0
                lab.append(_poisson(rng, sz * 5 * (1 + 1.6 * lab_dust)))
            data[a].update(resp_visits=resp, heat_visits=heat, lab_resp_pos=lab)
        else:
            hi, aqi = env[info["parent"]]
            w = info["workers"]
            absn, inc = [], []
            for i, d in enumerate(DATES):
                heat_s = _ramp(d, date(2025, 7, 15), s1["peak"], s1["end"]) if a == "gbc_site_a" else 0
                dust_s = _ramp(d, date(2025, 8, 24), s2["peak"], s2["end"]) if a == "gbc_site_b" else 0
                absn.append(_poisson(rng, w * 0.015 * (1 + 1.5 * heat_s + 1.2 * dust_s)))
                inc.append(_poisson(rng, (0.6 + 0.12 * max(0, hi[i] - 42)) * w / 1000 * (1 + 4 * heat_s)))
            data[a].update(absence=absn, incidents=inc)

    # Realistic gaps: ~3% random missing per series, plus one multi-day feed outage.
    for a in data:
        for s, series in data[a].items():
            for i in range(len(series)):
                if rng.random() < 0.03:
                    series[i] = None
    out = DATES.index(date(2025, 7, 20))
    for i in range(out, out + 3):
        data["gbc_site_a"]["absence"][i] = None  # HR feed outage during the heat cluster
    return data
