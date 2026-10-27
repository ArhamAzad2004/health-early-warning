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
