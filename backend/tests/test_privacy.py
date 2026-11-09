"""Privacy matrix: every endpoint x every role. These are the guarantees the README promises."""
import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.engine import baseline_z, score_area
from app.main import app
from app.sim import AREAS, SIGNALS

client = TestClient(app)
ROLES = ["public_health", "employer_hse", "public"]
SITES = [a for a, i in AREAS.items() if i["type"] == "site"]
DISTRICTS = [a for a, i in AREAS.items() if i["type"] == "district"]
PERSONAL = ("person", "patient", "worker", "employee", "email", "phone", "staff", "user")
ALLOWED = {"workers"}  # a site's total headcount: one aggregate number, not a person


def get(path, **params):
    return client.get(path, params=params)


def visible_areas(role):
    return {a["id"] for a in get("/api/areas", role=role).json()}


def walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v)


def responses(role):
    """Every successful JSON response a role can get."""
    out = [get("/api/meta").json(), get("/api/areas", role=role).json(),
           get("/api/risk", date="2025-07-23", role=role).json(), get("/api/alerts", role=role).json()]
    out += [get("/api/signals", area_id=a, role=role).json() for a in visible_areas(role)]
    if role != "public":
        out += [get("/api/backtest", role=role).json(), get("/api/notifications", role=role).json()]
    return out


@pytest.mark.parametrize("role", ROLES)
def test_no_personal_fields(role):
    for body in responses(role):
        assert not [k for k in walk_keys(body) if k not in ALLOWED and any(p in k.lower() for p in PERSONAL)]


@pytest.mark.parametrize("role", ROLES)
def test_small_counts_never_recoverable(role):
    for area in visible_areas(role):
        for signal, rows in get("/api/signals", area_id=area, role=role).json()["signals"].items():
            for r in rows:
                if SIGNALS[signal]["count"]:
                    assert r["value"] not in (1, 2, 3, 4)
                if r["suppressed"]:
                    assert r["value"] is None and r["baseline"] is None and r["z"] is None
    for al in get("/api/alerts", role=role).json():
        for e in al.get("evidence", []):
            assert e["value"] not in (1, 2, 3, 4)
            if e["value"] is None:
                assert e["baseline"] is None and e["z"] is None


@pytest.mark.parametrize("role", ROLES)
def test_area_scope_on_every_endpoint(role):
    allowed = set(DISTRICTS) if role == "public" else set(SITES) if role == "employer_hse" else set(AREAS)
    assert visible_areas(role) == allowed
    assert {r["area_id"] for r in get("/api/risk", date="2025-07-23", role=role).json()} <= allowed
    assert {a["area_id"] for a in get("/api/alerts", role=role).json()} <= allowed
    for area in set(AREAS) - allowed:
        assert get("/api/signals", area_id=area, role=role).status_code == 404
    if role != "public":
        for s in get("/api/backtest", role=role).json()["scenarios"]:
            assert set(s["areas_hit"] + s["areas_affected"] + s["missed_areas"]) <= allowed


def test_public_gets_advisories_only():
    assert get("/api/backtest", role="public").status_code == 403
    for al in get("/api/alerts", role="public").json():
        assert not {"evidence", "contributions", "peak_risk", "assumptions"} & set(al)
    for area in DISTRICTS:
        assert set(get("/api/signals", area_id=area, role="public").json()["signals"]) <= {"heat_index", "aqi"}


@pytest.mark.parametrize("path", ["/api/areas", "/api/alerts", "/api/backtest", "/api/signals?area_id=deira"])
def test_unknown_role_rejected(path):
    assert client.get(path, params={"role": "admin"}).status_code == 422


def test_bad_inputs_rejected_cleanly():
    assert get("/api/risk", date="1999-01-01").status_code == 400
    assert get("/api/risk", date="not-a-date").status_code == 400
    assert get("/api/signals", area_id="../etc/passwd").status_code == 404


@pytest.mark.parametrize("path", ["/api/meta", "/api/alerts", "/api/backtest?role=public", "/no-such-page"])
def test_security_headers_on_every_response(path):
    headers = client.get(path).headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("role", ROLES)
def test_baselines_come_only_from_published_values(role):
    """If every shown baseline and z can be recomputed from shown values alone, they cannot reveal a hidden count."""
    for area in visible_areas(role):
        signals = get("/api/signals", area_id=area, role=role).json()["signals"]
        for s, rows in signals.items():
            expected = baseline_z([r["value"] for r in rows], SIGNALS[s]["count"])
            for r, (mean, z, _) in zip(rows, expected):
                if not r["suppressed"]:
                    assert (r["baseline"], r["z"]) == (mean, z), (area, s, r["date"])
        for al in get("/api/alerts", role=role).json():
            if al["area_id"] != area:
                continue
            for e in al.get("evidence", []):
                row = next(r for r in signals[e["signal"]] if r["date"] == e["date"])
                assert (e["baseline"], e["z"]) == (row["baseline"], row["z"])


def test_employer_backtest_counts_only_its_sites():
    b = get("/api/backtest", role="employer_hse").json()
    alerts = get("/api/alerts", role="employer_hse").json()
    assert b["total_alerts"] == len(alerts)
    for s in b["scenarios"]:
        assert set(s["areas_affected"]) <= set(SITES)
        assert s["first_alert"] is None or s["first_alert"] in {a["start"] for a in alerts}


def test_server_errors_keep_headers_and_hide_details(monkeypatch):
    monkeypatch.setattr(main_module, "SCORES", {})
    r = TestClient(app, raise_server_exceptions=False).get("/api/signals", params={"area_id": "deira"})
    assert r.status_code == 500
    assert r.headers["x-frame-options"] == "DENY"
    assert "Traceback" not in r.text and "KeyError" not in r.text


def test_employer_and_public_risk_come_only_from_published_values():
    """Risk on the employer and public views must be reproducible from published values alone."""
    for area in AREAS:
        published = {s: [r["value"] for r in rows]
                     for s, rows in get("/api/signals", area_id=area).json()["signals"].items()}
        risk = [d["risk"] for d in score_area(published)[1]]
        for role in ("employer_hse", "public"):
            if area not in visible_areas(role):
                continue
            assert [r["risk"] for r in get("/api/signals", area_id=area, role=role).json()["risk"]] == risk
            assert {r["area_id"]: r["risk"] for r in get("/api/risk", date="2025-07-23", role=role).json()}[area] == risk[83]
    for al in get("/api/alerts", role="employer_hse").json():
        rows = get("/api/signals", area_id=al["area_id"], role="employer_hse").json()["risk"]
        assert al["peak_risk"] == max(r["risk"] for r in rows if al["start"] <= r["date"] <= al["end"])
        assert all(e["share"] == al["contributions"][e["signal"]] for e in al["evidence"])


def test_authority_keeps_full_fidelity_risk():
    from app.main import ALERTS
    shown = {a["id"]: a["peak_risk"] for a in get("/api/alerts", role="public_health").json()}
    assert shown == {a["id"]: a["peak_risk"] for a in ALERTS}


def test_employer_scenario_names_do_not_mention_districts():
    names = " ".join(s["name"] for s in get("/api/backtest", role="employer_hse").json()["scenarios"])
    assert not any(AREAS[d]["name"] in names for d in DISTRICTS)
