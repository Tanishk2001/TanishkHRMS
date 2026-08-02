import datetime as dt

from tests.conftest import auth


def _today():
    return dt.date.today().isoformat()


def test_my_projects_endpoint_scoped_to_self(client, tokens):
    r = client.get("/api/v1/employees/me/projects", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    names = {p["name"] for p in r.json()}
    assert "HR Policy Copilot" in names
    assert "Legacy Payroll Migration" not in names  # not assigned to this one


def test_seeded_time_entries_visible_to_owner(client, tokens):
    r = client.get("/api/v1/time-entries/me", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    assert len(r.json()) >= 3
    assert all(e["project_name"] == "HR Policy Copilot" for e in r.json())


def test_cannot_log_time_against_unassigned_project(client, tokens):
    r = client.post("/api/v1/time-entries", json={"project_id": 3, "work_date": _today(), "hours": 2},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 422
    assert "assigned" in r.json()["detail"].lower()


def test_negative_and_zero_hours_rejected(client, tokens):
    for bad_hours in (0, -1):
        r = client.post("/api/v1/time-entries", json={"project_id": 1, "work_date": _today(), "hours": bad_hours},
                         headers=auth(tokens["employee"]))
        assert r.status_code == 422


def test_single_entry_over_24h_rejected(client, tokens):
    r = client.post("/api/v1/time-entries", json={"project_id": 1, "work_date": _today(), "hours": 25},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 422


def test_daily_cap_enforced_across_multiple_entries(client, tokens):
    work_date = (dt.date.today() + dt.timedelta(days=40)).isoformat()
    r1 = client.post("/api/v1/time-entries", json={"project_id": 1, "work_date": work_date, "hours": 20},
                      headers=auth(tokens["employee"]))
    assert r1.status_code == 201

    r2 = client.post("/api/v1/time-entries", json={"project_id": 1, "work_date": work_date, "hours": 5},
                      headers=auth(tokens["employee"]))
    assert r2.status_code == 422
    assert "24" in r2.json()["detail"]


def test_log_and_delete_own_entry(client, tokens):
    work_date = (dt.date.today() + dt.timedelta(days=41)).isoformat()
    created = client.post("/api/v1/time-entries", json={"project_id": 1, "work_date": work_date, "hours": 3},
                           headers=auth(tokens["employee"])).json()

    r = client.delete(f"/api/v1/time-entries/{created['id']}", headers=auth(tokens["employee"]))
    assert r.status_code == 204


def test_cannot_delete_someone_elses_entry(client, tokens):
    team = client.get("/api/v1/time-entries/team", headers=auth(tokens["manager"])).json()
    priya_entry_id = next(e["id"] for e in team if e["employee_name"] == "Priya Dev")

    r = client.delete(f"/api/v1/time-entries/{priya_entry_id}", headers=auth(tokens["employee"]))
    assert r.status_code == 403

    team_after = client.get("/api/v1/time-entries/team", headers=auth(tokens["manager"])).json()
    assert any(e["id"] == priya_entry_id for e in team_after)


def test_employee_cannot_view_team_time_entries(client, tokens):
    r = client.get("/api/v1/time-entries/team", headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_manager_can_view_team_time_entries(client, tokens):
    r = client.get("/api/v1/time-entries/team", headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert len(r.json()) >= 6


def test_sql_agent_my_hours_this_week(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "How many hours have I logged this week?"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1


def test_sql_agent_project_hours_denied_for_employee(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "How many hours logged on HR Policy Copilot?"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is False
    assert "permission" in body["error"].lower()


def test_sql_agent_project_hours_allowed_for_manager(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "How many hours logged on HR Policy Copilot?"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1
