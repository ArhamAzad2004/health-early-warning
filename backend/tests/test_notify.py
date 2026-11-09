"""Notifications: each responsible role is told the day an alert opens, scoped by role."""
from fastapi.testclient import TestClient

from app.main import app
from app.sim import AREAS

client = TestClient(app)


def notes(**params):
    return client.get("/api/notifications", params=params)


def test_heat_cluster_notifies_site_and_district_owners():
    sent = {(n["area_id"], n["to"]): n["date"] for n in notes().json()}
    assert sent[("gbc_site_a", "Site HSE Manager (Gulf Build Co.)")] == "2025-07-20"
    assert sent[("jebel_ali", "District Public Health Officer")] == "2025-07-18"


def test_replay_date_limits_what_has_been_sent():
    before = notes(date="2025-07-19").json()
    assert all(n["date"] <= "2025-07-19" for n in before)
    assert len(before) < len(notes(date="2025-09-30").json())


def test_scoped_by_role():
    assert notes(role="public").status_code == 403
    assert {AREAS[n["area_id"]]["type"] for n in notes(role="employer_hse").json()} == {"site"}


def test_bad_date_rejected():
    assert notes(date="2030-01-01").status_code == 400


def test_notifications_carry_no_numbers():
    for n in notes().json():
        assert not [k for k, v in n.items() if isinstance(v, (int, float))]
