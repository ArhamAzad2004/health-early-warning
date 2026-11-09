import json
import logging
import os
import time
import urllib.request
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import engine
from .sim import AREAS, DATES, SCENARIOS, SIGNALS, generate

app = FastAPI(title="Sentinel Dubai – health early warning")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Strict-Transport-Security": "max-age=31536000",
}


@app.middleware("http")
async def security_headers(request, call_next):
    # shortcut: no Content-Security-Policy yet; Google Fonts, map tiles and Vite's inline styles need an allow-list
    try:
        response = await call_next(request)
    except Exception:  # crashes would otherwise skip this middleware and leak no headers but also no safe body
        logging.exception("Unhandled error on %s", request.url.path)
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    response.headers.update(SECURITY_HEADERS)
    return response

_started = time.monotonic()
DATA = generate()
SCORES, ALERTS = engine.run(DATA)
BACKTEST = engine.backtest(DATA, ALERTS)
BACKTEST_SITES = engine.backtest(DATA, ALERTS, scope=lambda a: AREAS[a]["type"] == "site")  # employer role
for _s in BACKTEST_SITES["scenarios"]:  # full scenario names mention districts the employer role cannot see
    _s["name"] = next(sc["short"] for sc in SCENARIOS if sc["id"] == _s["id"])
STARTUP_SECONDS = round(time.monotonic() - _started, 1)
BUILD = os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]  # logged only: a public build id would tell attackers which fixes are live
logging.getLogger("uvicorn.error").info("Generated %d areas, %d alerts and the back-test in %.1f s (build %s)",
                                        len(AREAS), len(ALERTS), STARTUP_SECONDS, BUILD)
DATE_INDEX = {d.isoformat(): i for i, d in enumerate(DATES)}

LIVE_CACHE = []  # [fetched_at, result]; protects the free Open-Meteo quota once the demo is public
Role = Query("public_health", pattern="^(public_health|employer_hse|public)$")
ENV = {"heat_index", "aqi"}


def visible(role, area_id):
    t = AREAS[area_id]["type"]
    return role == "public_health" or (role == "employer_hse" and t == "site") or (role == "public" and t == "district")


def suppress(signal, v):
    """Small-cell suppression: health/work counts of 1-4 are never shown."""
    if v is not None and SIGNALS[signal]["count"] and 0 < v < 5:
        return None, True
    return v, False


def published(signal, values):
    """A series as users see it: suppressed and missing days are unknown."""
    return [None if v is None or suppress(signal, v)[1] else v for v in values]


# Derived numbers are recomputed from published values only, so no combination of numbers on
# screen can reveal a hidden count: baselines and z-scores for every role; risk, peak risk and
# contributions for the employer and public roles. The public health authority legitimately holds
# the full data, so it keeps full-fidelity risk. Detection and alerts always use the full data.
PUBLIC = {a: engine.score_area({s: published(s, v) for s, v in sc["series"].items()}) for a, sc in SCORES.items()}
PUBLIC_Z = {a: zs for a, (zs, _) in PUBLIC.items()}
PUBLIC_DAYS = {a: days for a, (_, days) in PUBLIC.items()}


@app.get("/api/meta")
def meta():
    return dict(start=DATES[0].isoformat(), end=DATES[-1].isoformat(), signals=SIGNALS,
                levels=dict(watch=engine.WATCH, warning=engine.WARNING, alert=engine.ALERT),
                scenarios=[dict(id=s["id"], short=s["short"], peak=s["peak"].isoformat()) for s in SCENARIOS])  # no site names: public role reads this too


@app.get("/api/areas")
def areas(role: str = Role):
    return [dict(id=a, **info) for a, info in AREAS.items() if visible(role, a)]


@app.get("/api/signals")
def signals(area_id: str, role: str = Role):
    if area_id not in AREAS or not visible(role, area_id):
        raise HTTPException(404, "Area not visible for this role")
    sc = SCORES[area_id]
    out = {}
    for s, values in sc["series"].items():
        if role == "public" and s not in ENV:
            continue
        rows = []
        for i, v in enumerate(values):
            val, sup = suppress(s, v)
            mean, z, _ = PUBLIC_Z[area_id][s][i]
            if sup:
                mean = z = None
            rows.append(dict(date=DATES[i].isoformat(), value=val, suppressed=sup, missing=v is None, baseline=mean, z=z))
        out[s] = rows
    days = sc["days"] if role == "public_health" else PUBLIC_DAYS[area_id]
    risk = [dict(date=DATES[i].isoformat(), risk=d["risk"], level=engine.level(d["risk"])) for i, d in enumerate(days)]
    return dict(area_id=area_id, signals=out, risk=risk)


@app.get("/api/risk")
def risk(date: str, role: str = Role):
    if date not in DATE_INDEX:
        raise HTTPException(400, f"date must be between {DATES[0]} and {DATES[-1]}")
    i = DATE_INDEX[date]
    out = []
    for a in AREAS:
        if not visible(role, a):
            continue
        r = (SCORES[a]["days"] if role == "public_health" else PUBLIC_DAYS[a])[i]["risk"]
        out.append(dict(area_id=a, risk=r, level=engine.level(r), missing=SCORES[a]["days"][i]["missing"]))
    return out


def hide_small(area_id, e):
    """Evidence row as users may see it: 1-4 counts blanked, baseline and z from published values only."""
    val, sup = suppress(e["signal"], e["value"])
    if sup:
        return dict(e, value=None, baseline=None, z=None)
    mean, z, _ = PUBLIC_Z[area_id][e["signal"]][DATE_INDEX[e["date"]]]
    return dict(e, baseline=mean, z=z)


def public_alert(al):
    """An alert as users see it: peak risk and contributions recomputed from published values."""
    days = PUBLIC_DAYS[al["area_id"]][DATE_INDEX[al["start"]]:DATE_INDEX[al["end"]] + 1]
    totals = {s: sum(d["contrib"][s] for d in days) for s in days[0]["contrib"]}
    total = sum(totals.values()) or 1
    shares = {s: round(v / total, 3) for s, v in sorted(totals.items(), key=lambda kv: -kv[1])}
    return dict(al, peak_risk=max(d["risk"] for d in days), contributions=shares,
                evidence=[dict(hide_small(al["area_id"], e), share=shares[e["signal"]]) for e in al["evidence"]])


PUBLIC_ALERTS = [public_alert(al) for al in ALERTS]
AUTHORITY_ALERTS = [dict(al, evidence=[hide_small(al["area_id"], e) for e in al["evidence"]]) for al in ALERTS]


@app.get("/api/alerts")
def alerts(role: str = Role):
    out = [al for al in (AUTHORITY_ALERTS if role == "public_health" else PUBLIC_ALERTS) if visible(role, al["area_id"])]
    if role == "public":  # the public sees advisories, not the underlying health counts
        out = [{k: v for k, v in al.items() if k in ("id", "area_id", "area", "start", "end", "level", "action", "category")} for al in out]
    return out


# One notification per responsible role when an alert opens. Built only from alert metadata
# (area, dates, level, action), so it carries no counts and needs no extra privacy handling.
NOTIFICATIONS = [dict(id=f"{al['id']}-{i}", alert_id=al["id"], area_id=al["area_id"], area=al["area"], date=al["start"],
                      to=to, level=al["level"], category=al["category"], action=al["action"])
                 for al in ALERTS for i, to in enumerate(al["roles"])]


@app.get("/api/notifications")
def notifications(role: str = Role, date: str | None = None):
    """Who was told what, and when, up to an optional replay date."""
    if role == "public":
        raise HTTPException(403, "Notifications are for public health and employer roles")
    if date is not None and date not in DATE_INDEX:
        raise HTTPException(400, f"date must be between {DATES[0]} and {DATES[-1]}")
    return [n for n in NOTIFICATIONS if visible(role, n["area_id"]) and (date is None or n["date"] <= date)]


@app.get("/api/backtest")
def backtest(role: str = Role):
    if role == "public":
        raise HTTPException(403, "Validation detail is for public health and employer roles")
    return BACKTEST_SITES if role == "employer_hse" else BACKTEST


@app.get("/api/live")
def live():
    """Current Dubai weather and air quality from Open-Meteo (free, no key), cached for 10 minutes."""
    if LIVE_CACHE and time.monotonic() - LIVE_CACHE[0] < 600:
        return LIVE_CACHE[1]
    lat, lon = 25.2048, 55.2708
    urls = {
        "weather": f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                   "&current=temperature_2m,relative_humidity_2m,apparent_temperature&timezone=Asia%2FDubai",
        "air": f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
               "&current=pm10,pm2_5,us_aqi,dust&timezone=Asia%2FDubai",
    }
    try:
        got = {k: json.load(urllib.request.urlopen(u, timeout=6))["current"] for k, u in urls.items()}
    except Exception:  # offline demo must still work
        return dict(ok=False, error="unavailable", fetched=date.today().isoformat())
    w, a = got["weather"], got["air"]
    result = dict(ok=True, time=w["time"], temperature=w["temperature_2m"], humidity=w["relative_humidity_2m"],
                feels_like=w["apparent_temperature"], pm10=a.get("pm10"), pm2_5=a.get("pm2_5"),
                us_aqi=a.get("us_aqi"), dust=a.get("dust"), source="Open-Meteo")
    LIVE_CACHE[:] = [time.monotonic(), result]
    return result


# Serve the built dashboard from the same app, so one link runs the whole demo. Mounted last so /api wins.
STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")
