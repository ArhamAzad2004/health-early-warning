import json
import logging
import os
import threading
import time
import urllib.request
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import engine
from .sim import AREAS, DATES, SCENARIOS, SIGNALS, generate

log = logging.getLogger("uvicorn.error")
# API docs pages are on for local development and off in the Docker image (API_DOCS=0): the public site
# doesn't need an interactive map of every endpoint, and the pages load scripts from a CDN.
_docs = os.environ.get("API_DOCS", "1") == "1"
app = FastAPI(title="Sentinel Dubai – health early warning",
              docs_url="/docs" if _docs else None, redoc_url="/redoc" if _docs else None,
              openapi_url="/openapi.json" if _docs else None)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # Send only our origin cross-site (never paths): OpenStreetMap blocks map tiles requested without a Referer.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Strict-Transport-Security": "max-age=31536000",
    # Only our own scripts run; the outside hosts are Google Fonts and the OSM map tiles.
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        "img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self'; "
        "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
}
API_DOCS = {"/docs", "/redoc"}  # FastAPI's docs pages load Swagger/ReDoc from a CDN with inline scripts, so they skip the CSP


@app.middleware("http")
async def security_headers(request, call_next):
    try:
        response = await call_next(request)
    except Exception:  # a crash must still get the headers and a generic body, never a traceback
        log.exception("Unhandled error on %s", request.url.path)
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    response.headers.update(SECURITY_HEADERS)
    if request.url.path in API_DOCS:
        del response.headers["Content-Security-Policy"]
    return response

_started = time.monotonic()
DATA = generate()
SCORES, ALERTS = engine.run(DATA)
DATE_INDEX = {d.isoformat(): i for i, d in enumerate(DATES)}

LIVE_CACHE = []  # [fetched_at, result, ttl]; protects the free Open-Meteo quota once the demo is public
LIVE_UA = "sentinel-dubai/1.0 (+https://sentinel-dubai.onrender.com)"
LIVE_LOCK = threading.Lock()  # one upstream refresh at a time; others get the last answer, so a burst can't tie up threads
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
# contributions for the employer and public roles (who get no peak risk at all). The public health authority legitimately holds
# the full data, so it keeps full-fidelity risk. Detection and alerts always use the full data.
PUBLIC = {a: engine.score_area({s: published(s, v) for s, v in sc["series"].items()}) for a, sc in SCORES.items()}
PUBLIC_Z = {a: zs for a, (zs, _) in PUBLIC.items()}
PUBLIC_DAYS = {a: days for a, (_, days) in PUBLIC.items()}
PUBLISHED_DATA = {a: {s: published(s, v) for s, v in series.items()} for a, series in DATA.items()}

# Detection metrics use the full data; the impact estimate (counts) uses published values only.
BACKTEST = engine.backtest(DATA, ALERTS, impact_data=PUBLISHED_DATA)
BACKTEST_SITES = engine.backtest(DATA, ALERTS, scope=lambda a: AREAS[a]["type"] == "site", impact_data=PUBLISHED_DATA)  # employer role
for _s in BACKTEST_SITES["scenarios"]:  # full scenario names mention districts the employer role cannot see
    _s["name"] = next(sc["short"] for sc in SCENARIOS if sc["id"] == _s["id"])
STARTUP_SECONDS = round(time.monotonic() - _started, 1)
BUILD = os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]  # logged only: a public build id would tell attackers which fixes are live
log.info("Generated %d areas, %d alerts and the back-test in %.1f s (build %s)",
         len(AREAS), len(ALERTS), STARTUP_SECONDS, BUILD)


def focus(sc, role):
    """The day a scenario looks most alarming on this role's map (highest risk in the areas it may see): what
    "Jump to" opens. The harm peak itself comes later, when the alerts have done their job and risk is easing.
    Uses the same risk the role's map shows, so it reveals nothing that role can't already see."""
    areas = [a for a in sc["areas"] if visible(role, a)]
    if not areas:
        return sc["peak"].isoformat()
    risk = (lambda a, i: SCORES[a]["days"][i]["risk"]) if role == "public_health" else (lambda a, i: PUBLIC_DAYS[a][i]["risk"])
    days = [d for d in DATES if sc["start"] <= d <= sc["end"]]
    return max(days, key=lambda d: max(risk(a, DATE_INDEX[d.isoformat()]) for a in areas)).isoformat()


@app.get("/api/meta")
def meta(role: str = Role):
    return dict(start=DATES[0].isoformat(), end=DATES[-1].isoformat(), signals=SIGNALS,
                levels=dict(watch=engine.WATCH, warning=engine.WARNING, alert=engine.ALERT),
                scenarios=[dict(id=s["id"], short=s["short"], peak=s["peak"].isoformat(), focus=focus(s, role))
                           for s in SCENARIOS])  # no site names: public role reads this too


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
    _, sup = suppress(e["signal"], e["value"])
    if sup:
        return dict(e, value=None, baseline=None, z=None)
    mean, z, _ = PUBLIC_Z[area_id][e["signal"]][DATE_INDEX[e["date"]]]
    return dict(e, baseline=mean, z=z)


def public_alert(al):
    """An alert as employer and public users see it: contributions recomputed from published values."""
    days = PUBLIC_DAYS[al["area_id"]][DATE_INDEX[al["start"]]:DATE_INDEX[al["end"]] + 1]
    totals = {s: sum(d["contrib"][s] for d in days) for s in days[0]["contrib"]}
    total = sum(totals.values()) or 1
    shares = {s: round(v / total, 3) for s, v in sorted(totals.items(), key=lambda kv: -kv[1])}
    # No peak risk: the official level and advice are shared as issued, and a published peak below the level's
    # threshold would show how much the hidden counts added.
    return dict({k: v for k, v in al.items() if k != "peak_risk"}, contributions=shares,
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
    if LIVE_CACHE and time.monotonic() - LIVE_CACHE[0] < LIVE_CACHE[2]:
        return LIVE_CACHE[1]
    if not LIVE_LOCK.acquire(blocking=False):  # another request is refreshing
        if LIVE_CACHE:
            return LIVE_CACHE[1]  # answer with the last result instead of queueing
        if not LIVE_LOCK.acquire(timeout=15):  # nothing cached yet (fresh start): wait for that first fetch
            return dict(ok=False, error="unavailable", fetched=date.today().isoformat())
        LIVE_LOCK.release()
        return LIVE_CACHE[1] if LIVE_CACHE else dict(ok=False, error="unavailable", fetched=date.today().isoformat())
    try:
        result, ttl = _fetch_live()
        LIVE_CACHE[:] = [time.monotonic(), result, ttl]
        return result
    finally:
        LIVE_LOCK.release()


def _fetch_live():
    """(result, seconds to cache it): 10 minutes when fresh, 1 minute after a failure so retries stay cheap."""
    lat, lon = 25.2048, 55.2708
    urls = {
        "weather": f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                   "&current=temperature_2m,relative_humidity_2m,apparent_temperature&timezone=Asia%2FDubai",
        "air": f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
               "&current=pm10,pm2_5,us_aqi,dust&timezone=Asia%2FDubai",
    }
    try:
        # A named client instead of urllib's default "Python-urllib" agent, which shared hosts often block.
        got = {k: json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": LIVE_UA}), timeout=6))["current"]
               for k, u in urls.items()}
        w, a = got["weather"], got["air"]
        result = dict(ok=True, time=w["time"], temperature=w["temperature_2m"], humidity=w["relative_humidity_2m"],
                      feels_like=w["apparent_temperature"], pm10=a.get("pm10"), pm2_5=a.get("pm2_5"),
                      us_aqi=a.get("us_aqi"), dust=a.get("dust"), source="Open-Meteo")
    except Exception as e:  # noqa: BLE001 - any upstream failure (offline, timeout, bad JSON) falls back; the demo must still work
        log.warning("Live weather unavailable: %.200r", e)  # without this a hosted-only failure is invisible
        return dict(ok=False, error="unavailable", fetched=date.today().isoformat()), 60
    return result, 600


# Serve the built dashboard from the same app, so one link runs the whole demo. Mounted last so /api wins.
STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")
