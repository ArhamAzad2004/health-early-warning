"""Self-checks for the demo path: both scenarios caught early, few false alarms, privacy holds."""
from fastapi.testclient import TestClient

from app.main import BACKTEST, app

client = TestClient(app)


def test_scenarios_detected_before_peak():
    assert BACKTEST["sensitivity"] == 1.0
    assert all(s["lead_time_days"] >= 2 for s in BACKTEST["scenarios"])
    assert BACKTEST["false_alarms"] <= 2


def test_missed_areas_reported_as_known_limit():
    by_id = {s["id"]: s for s in BACKTEST["scenarios"]}
    # S2: GBC Site B only had its absence signal in window, never corroborated on two consecutive days.
    assert by_id["S2"]["missed_areas"] == ["gbc_site_b"]
    assert by_id["S1"]["missed_areas"] == []
    assert "consecutive" in by_id["S2"]["known_limit"]


def test_small_cells_suppressed():
    rows = client.get("/api/signals", params={"area_id": "gbc_site_a"}).json()["signals"]["incidents"]
    assert all(r["value"] is None or r["value"] == 0 or r["value"] >= 5 for r in rows)
    assert any(r["suppressed"] for r in rows)


def test_roles_limit_views():
    assert {a["type"] for a in client.get("/api/areas", params={"role": "employer_hse"}).json()} == {"site"}
    assert {a["type"] for a in client.get("/api/areas", params={"role": "public"}).json()} == {"district"}
    assert client.get("/api/signals", params={"area_id": "gbc_site_a", "role": "public"}).status_code == 404
    pub = client.get("/api/alerts", params={"role": "public"}).json()
    assert pub and all("evidence" not in a for a in pub)


def test_alert_explains_itself():
    al = client.get("/api/alerts").json()[0]
    assert al["contributions"] and al["evidence"] and al["roles"] and al["action"] and al["assumptions"]


def test_pitch_numbers_unchanged():
    """These numbers are quoted in README, docs/PRD.md, docs/TRD.md and the slides.
    If tuning changes them on purpose, update those places and then this test."""
    assert BACKTEST["sensitivity"] == 1.0
    assert BACKTEST["area_sensitivity"] == 0.8
    assert BACKTEST["ppv"] == 0.8
    assert BACKTEST["false_alarms"] == 1
    assert [s["lead_time_days"] for s in BACKTEST["scenarios"]] == [5, 3]


def test_meta_lists_demo_scenarios():
    scenarios = client.get("/api/meta").json()["scenarios"]
    assert [s["short"] for s in scenarios] == ["Heat cluster", "Dust storm"]


def test_suppressed_cells_reveal_nothing():
    """Baseline and z on a hidden cell would let anyone rebuild the 1-4 count."""
    for role, area in [("employer_hse", "gbc_site_a"), ("public_health", "jebel_ali")]:
        for rows in client.get("/api/signals", params={"area_id": area, "role": role}).json()["signals"].values():
            assert all(r["baseline"] is None and r["z"] is None for r in rows if r["suppressed"])
    for al in client.get("/api/alerts").json():
        assert all(e["baseline"] is None and e["z"] is None for e in al["evidence"] if e["value"] is None)


def test_location_reliability_lowers_confidence_only():
    from app.main import ALERTS
    for al in ALERTS:
        assert 0 <= al["location_reliability"] <= 1
    qusais = next(al for al in ALERTS if al["area_id"] == "al_qusais")
    assert qusais["location_reliability"] < 0.8 and qusais["completeness"] >= 0.9
    assert qusais["confidence"] == "medium"  # would be "high" on completeness alone


def test_unknown_location_stress_row():
    row = next(m for m in BACKTEST["missing_input"] if m["without"] == "unknown_location")
    assert row["sensitivity"] == 1.0 and row["mean_lead_time_days"] is not None


def test_jump_days_show_each_outbreak_at_alert_level():
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    for sc in c.get("/api/meta").json()["scenarios"]:
        assert sc["focus"] <= sc["peak"]
        levels = {r["level"] for r in c.get("/api/risk", params={"date": sc["focus"]}).json()}
        assert "alert" in levels, sc
    # Other roles get the day from the areas they can see, on the risk their map shows: the focus day is
    # at least as alarming as the harm peak. (The employer's only dust-storm area is Site B, the known miss.)
    for role in ("employer_hse", "public"):
        top = lambda d: max(r["risk"] for r in c.get("/api/risk", params={"date": d, "role": role}).json())  # noqa: B023
        for sc in c.get("/api/meta", params={"role": role}).json()["scenarios"]:
            assert top(sc["focus"]) >= top(sc["peak"]), (role, sc)
    public = {s["id"]: s["focus"] for s in c.get("/api/meta", params={"role": "public"}).json()["scenarios"]}
    assert public["S1"] == "2025-07-22"  # from Jebel Ali district only, never from the GBC site the public can't see


def test_docker_lock_matches_requirements():
    """The Docker image installs requirements-lock.txt; it must pin the same top-level versions as requirements.txt."""
    import re
    from pathlib import Path
    here = Path(__file__).resolve().parents[1]
    norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
    lock = {norm(n): v for n, v in re.findall(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", (here / "requirements-lock.txt").read_text(), re.MULTILINE)}
    for name, version in re.findall(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?==(\S+)", (here / "requirements.txt").read_text(), re.MULTILINE):
        assert lock.get(norm(name)) == version, f"{name}: requirements.txt {version}, lock {lock.get(norm(name))}"
