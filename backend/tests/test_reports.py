from tests.conftest import auth


def test_headcount_report_admin(client, tokens):
    r = client.get("/api/v1/reports/headcount", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    body = r.json()
    # Total population is stable at 4 seeded employees, but the
    # active/inactive split isn't a safe thing to assert an exact
    # value for here — test_exits.py (which runs earlier alphabetically)
    # completes a real offboarding during the session, so total_inactive
    # may legitimately be >0 by the time this test runs.
    assert body["total_active"] + body["total_inactive"] >= 4
    assert body["total_inactive"] >= 0
    depts = {d["department"] for d in body["by_department"]}
    assert "Engineering" in depts
    assert body["by_role"]["ADMIN"] >= 1
    assert body["by_role"]["MANAGER"] >= 1
    # >= 1 not >= 2: test_exits.py (runs earlier alphabetically) completes
    # a real offboarding for one of the two seeded EMPLOYEE-role accounts.
    assert body["by_role"]["EMPLOYEE"] >= 1


def test_leave_trends_report_admin(client, tokens):
    r = client.get("/api/v1/reports/leave-trends", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    body = r.json()
    assert "by_type" in body
    assert body["total_requests_last_90_days"] >= 0


def test_attendance_trends_report_admin(client, tokens):
    r = client.get("/api/v1/reports/attendance-trends", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    body = r.json()
    assert len(body["last_14_days"]) >= 1
    assert 0.0 <= body["late_rate_pct"] <= 100.0


def test_tickets_report_admin(client, tokens):
    r = client.get("/api/v1/reports/tickets", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    body = r.json()
    assert "by_status" in body
    assert "by_priority" in body


def test_reports_denied_for_employee(client, tokens):
    for path in ("headcount", "leave-trends", "attendance-trends", "tickets"):
        r = client.get(f"/api/v1/reports/{path}", headers=auth(tokens["employee"]))
        assert r.status_code == 403, path


def test_reports_denied_for_manager(client, tokens):
    # Analytics is scoped admin-only by design — managers already have
    # team-scoped views elsewhere (attendance/team, pending leaves).
    r = client.get("/api/v1/reports/headcount", headers=auth(tokens["manager"]))
    assert r.status_code == 403


def test_reports_reflect_real_leave_activity(client, tokens):
    # test_actions.py already applies several leave requests over the
    # course of the suite; by the time this runs, at least one CASUAL
    # or SICK type should show up here with a nonzero count.
    r = client.get("/api/v1/reports/leave-trends", headers=auth(tokens["admin"]))
    body = r.json()
    total_across_types = sum(t["approved"] + t["pending"] + t["rejected"] for t in body["by_type"])
    assert total_across_types >= 1


def test_reports_reflect_real_ticket_activity(client, tokens):
    # test_actions.py creates at least one ticket earlier in the suite.
    r = client.get("/api/v1/reports/tickets", headers=auth(tokens["admin"]))
    body = r.json()
    total = sum(s["count"] for s in body["by_status"])
    assert total >= 1
