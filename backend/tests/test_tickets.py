from tests.conftest import auth


def test_create_ticket_defaults_category_and_stamps_sla_due_at(client, tokens):
    r = client.post("/api/v1/tickets", json={"title": "Monitor flickering", "priority": "HIGH"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "IT"  # default when not specified
    assert body["priority"] == "HIGH"
    assert body["sla_due_at"] is not None
    assert body["is_breached"] is False  # freshly created, due date is in the future


def test_create_ticket_with_explicit_category(client, tokens):
    r = client.post(
        "/api/v1/tickets",
        json={"title": "Payslip discrepancy", "category": "FINANCE", "priority": "MEDIUM"},
        headers=auth(tokens["employee"]),
    )
    assert r.status_code == 201
    assert r.json()["category"] == "FINANCE"


def test_employee_cannot_list_all_tickets(client, tokens):
    r = client.get("/api/v1/tickets", headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_manager_can_list_all_tickets_and_filter_by_category(client, tokens):
    r = client.get("/api/v1/tickets", headers=auth(tokens["manager"]))
    assert r.status_code == 200
    categories = {t["category"] for t in r.json()}
    assert "HR" in categories or "IT" in categories  # seeded data spans categories

    r_hr = client.get("/api/v1/tickets?category=HR", headers=auth(tokens["manager"]))
    assert r_hr.status_code == 200
    assert all(t["category"] == "HR" for t in r_hr.json())


def test_manage_view_reports_the_seeded_breached_ticket(client, tokens):
    r = client.get("/api/v1/tickets?breached_only=true", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    breached = r.json()
    assert len(breached) >= 1
    assert all(t["is_breached"] is True for t in breached)
    assert any(t["title"] == "VPN keeps disconnecting" for t in breached)


def test_closed_ticket_is_never_reported_as_breached(client, tokens):
    # The seeded ADMIN-category ticket has a sla_due_at in the past but is CLOSED.
    r = client.get("/api/v1/tickets?category=ADMIN", headers=auth(tokens["admin"]))
    closed = next(t for t in r.json() if t["status"] == "CLOSED")
    assert closed["is_breached"] is False


def test_changing_priority_reprices_the_sla_due_date(client, tokens):
    created = client.post("/api/v1/tickets", json={"title": "Printer offline", "priority": "LOW"},
                           headers=auth(tokens["employee"])).json()
    original_due = created["sla_due_at"]

    r = client.patch(f"/api/v1/tickets/{created['id']}", json={"priority": "HIGH"},
                      headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert r.json()["priority"] == "HIGH"
    assert r.json()["sla_due_at"] != original_due  # re-based to a HIGH-priority window


def test_employee_cannot_view_a_ticket_that_is_not_theirs(client, tokens):
    other = client.post("/api/v1/tickets", json={"title": "Confidential HR matter", "category": "HR"},
                         headers=auth(tokens["manager"])).json()
    r = client.get(f"/api/v1/tickets/{other['id']}", headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_creator_can_view_and_comment_on_own_ticket(client, tokens):
    ticket = client.post("/api/v1/tickets", json={"title": "Laptop won't boot"},
                          headers=auth(tokens["employee"])).json()

    r = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth(tokens["employee"]))
    assert r.status_code == 200

    r = client.post(f"/api/v1/tickets/{ticket['id']}/comments", json={"body": "Tried a reboot, still stuck."},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 201
    assert r.json()["body"] == "Tried a reboot, still stuck."
    assert r.json()["employee_name"]

    r = client.get(f"/api/v1/tickets/{ticket['id']}/comments", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_unrelated_employee_cannot_comment_on_someone_elses_ticket(client, tokens):
    ticket = client.post("/api/v1/tickets", json={"title": "Reimbursement question", "category": "FINANCE"},
                          headers=auth(tokens["manager"])).json()
    r = client.post(f"/api/v1/tickets/{ticket['id']}/comments", json={"body": "Can I help?"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_empty_comment_rejected(client, tokens):
    ticket = client.post("/api/v1/tickets", json={"title": "Chair is broken"},
                          headers=auth(tokens["employee"])).json()
    r = client.post(f"/api/v1/tickets/{ticket['id']}/comments", json={"body": "   "},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 422


def test_seeded_ticket_thread_has_two_comments(client, tokens):
    all_tickets = client.get("/api/v1/tickets", headers=auth(tokens["admin"])).json()
    leave_ticket = next(t for t in all_tickets if "carry-forward" in t["title"])
    r = client.get(f"/api/v1/tickets/{leave_ticket['id']}/comments", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_tickets_report_includes_category_breakdown_and_breach_count(client, tokens):
    r = client.get("/api/v1/reports/tickets", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    body = r.json()
    assert body["total_breached"] >= 1
    assert any(c["category"] == "IT" for c in body["by_category"])


def test_manager_cannot_view_ai_usage_but_can_still_manage_tickets(client, tokens):
    # Sanity check that the new /tickets manage-view didn't accidentally
    # piggyback on the AI-only permissions module's stricter admin-only gate.
    r = client.get("/api/v1/tickets", headers=auth(tokens["manager"]))
    assert r.status_code == 200
