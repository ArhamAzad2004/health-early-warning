import json
import os
import time
import urllib.request
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import engine
from .sim import AREAS, DATES, SIGNALS, generate

app = FastAPI(title="Sentinel Dubai – health early warning")

DATA = generate()
SCORES, ALERTS = engine.run(DATA)
BACKTEST = engine.backtest(DATA, ALERTS)
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


@app.get("/api/meta")
def meta():
    return dict(start=DATES[0].isoformat(), end=DATES[-1].isoformat(), signals=SIGNALS,
                levels=dict(watch=engine.WATCH, warning=engine.WARNING, alert=engine.ALERT))


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
            mean, z, _ = sc["zs"][s][i]
            if sup:  # baseline + z would let anyone rebuild the hidden count
                mean = z = None
            rows.append(dict(date=DATES[i].isoformat(), value=val, suppressed=sup, missing=v is None, baseline=mean, z=z))
        out[s] = rows
    risk = [dict(date=DATES[i].isoformat(), risk=d["risk"], level=engine.level(d["risk"])) for i, d in enumerate(sc["days"])]
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
        d = SCORES[a]["days"][i]
        out.append(dict(area_id=a, risk=d["risk"], level=engine.level(d["risk"]), missing=d["missing"]))
    return out


def hide_small(e):
    """Evidence row with a 1-4 count blanked, along with the baseline and z that would reveal it."""
    val, sup = suppress(e["signal"], e["value"])
    return dict(e, value=val, baseline=None, z=None) if sup else e


@app.get("/api/alerts")
def alerts(role: str = Role):
    out = [dict(al, evidence=[hide_small(e) for e in al["evidence"]])
           for al in ALERTS if visible(role, al["area_id"])]
    if role == "public":  # the public sees advisories, not the underlying health counts
        out = [{k: v for k, v in al.items() if k in ("id", "area_id", "area", "start", "end", "level", "action", "category")} for al in out]
    return out


@app.get("/api/backtest")
def backtest(role: str = Role):
    if role == "public":
        raise HTTPException(403, "Validation detail is for public health and employer roles")
    return BACKTEST


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
