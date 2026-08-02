from tests.conftest import auth


def test_seeded_pending_exit_visible_to_manager(client, tokens):
    r = client.get("/api/v1/exits", headers=auth(tokens["manager"]))
    assert r.status_code == 200
    names = {e["employee_name"] for e in r.json()}
    assert "Priya Dev" in names


def test_employee_cannot_list_all_exits(client, tokens):
    r = client.get("/api/v1/exits", headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_duplicate_open_exit_request_rejected(client, tokens):
    r1 = client.post("/api/v1/exits", json={"last_working_day": "2026-10-01", "reason": "test A"},
                      headers=auth(tokens["admin"]))
    assert r1.status_code == 201
    r2 = client.post("/api/v1/exits", json={"last_working_day": "2026-10-15", "reason": "test B"},
                      headers=auth(tokens["admin"]))
    assert r2.status_code == 422


def test_full_exit_workflow_blocks_completion_until_assets_returned(client, tokens):
    # Uses the SEEDED pending exit request for Priya Dev rather than
    # resigning one of the shared fixture accounts (admin/manager/
    # employee) — completing an exit deactivates the employee, and
    # get_current_user() rejects inactive users, so deactivating any
    # of the three tokens shared across the whole test session would
    # break every other test file that authenticates as that role for
    # the rest of the run. Priya Dev has no token fixture, so it's safe.
    admin_dir = client.get("/api/v1/employees", headers=auth(tokens["admin"])).json()
    priya_id = next(e["id"] for e in admin_dir if e["name"] == "Priya Dev")

    exits = client.get("/api/v1/exits", headers=auth(tokens["manager"])).json()
    exit_id = next(e["id"] for e in exits if e["employee_id"] == priya_id and e["status"] == "PENDING")

    # her manager (Rahul) can decide it
    r = client.patch(f"/api/v1/exits/{exit_id}/decision", json={"status": "APPROVED"}, headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"

    # deciding twice is rejected
    r = client.patch(f"/api/v1/exits/{exit_id}/decision", json={"status": "APPROVED"}, headers=auth(tokens["manager"]))
    assert r.status_code == 422

    # checklist locked to admin, not even her manager
    r = client.patch(f"/api/v1/exits/{exit_id}/checklist", json={"knowledge_transfer_done": True},
                      headers=auth(tokens["manager"]))
    assert r.status_code == 403

    # complete blocked — nothing on the checklist done yet
    r = client.post(f"/api/v1/exits/{exit_id}/complete", headers=auth(tokens["admin"]))
    assert r.status_code == 422
    assert "asset return" in r.json()["detail"]

    r = client.patch(
        f"/api/v1/exits/{exit_id}/checklist",
        json={"knowledge_transfer_done": True, "exit_interview_done": True, "fnf_settled": True},
        headers=auth(tokens["admin"]),
    )
    assert r.json()["assets_returned"] is False  # she still holds LT-1002 per seed data

    # complete still blocked — asset not returned
    r = client.post(f"/api/v1/exits/{exit_id}/complete", headers=auth(tokens["admin"]))
    assert r.status_code == 422
    assert "asset return" in r.json()["detail"]

    # return her laptop (LT-1002)
    all_assets = client.get("/api/v1/assets", headers=auth(tokens["admin"])).json()
    laptop2_id = next(a["id"] for a in all_assets if a["asset_tag"] == "LT-1002")
    r = client.post(f"/api/v1/assets/{laptop2_id}/return", json={"condition_on_return": "GOOD"},
                     headers=auth(tokens["admin"]))
    assert r.status_code == 200

    # now completion succeeds
    r = client.post(f"/api/v1/exits/{exit_id}/complete", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["assets_returned"] is True

    # the active-only employee directory no longer lists her
    directory = client.get("/api/v1/employees", headers=auth(tokens["admin"])).json()
    assert not any(e["name"] == "Priya Dev" for e in directory)


def test_headcount_report_reflects_completed_exit(client, tokens):
    r = client.get("/api/v1/reports/headcount", headers=auth(tokens["admin"]))
    assert r.json()["total_inactive"] >= 1


def test_sql_agent_pending_exit_requests_denied_for_employee(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Who is resigning?"}, headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is False
    assert "permission" in body["error"].lower()
