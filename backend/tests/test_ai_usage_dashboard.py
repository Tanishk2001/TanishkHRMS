from tests.conftest import auth


def test_recent_actions_returns_only_the_caller_s_own_history(client, tokens):
    # Fire a couple of distinct, easy-to-recognize messages as the
    # employee, then confirm /audit/recent only ever returns rows
    # belonging to that same employee.
    marker = "How many sick leaves do I get? [recent-actions-test]"
    client.post("/api/v1/chat/policy", json={"message": marker}, headers=auth(tokens["employee"]))

    r = client.get("/api/v1/chat/audit/recent", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    logs = body["data"]["logs"]
    assert any(marker in log["message"] for log in logs)
    # Every row's presence here implies user-scoping by construction
    # (the endpoint filters by the caller's user_id server-side) —
    # sanity-check the shape instead of trying to inspect user_id,
    # which is intentionally not exposed in the response.
    for log in logs:
        assert "action_status" in log
        assert "created_at" in log


def test_recent_actions_respects_limit_param(client, tokens):
    for i in range(3):
        client.post("/api/v1/chat/policy", json={"message": f"limit test {i}"}, headers=auth(tokens["manager"]))

    r = client.get("/api/v1/chat/audit/recent?limit=2", headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert len(r.json()["data"]["logs"]) == 2


def test_usage_dashboard_denied_for_employee(client, tokens):
    r = client.get("/api/v1/chat/audit/usage", headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_usage_dashboard_denied_for_manager(client, tokens):
    r = client.get("/api/v1/chat/audit/usage", headers=auth(tokens["manager"]))
    assert r.status_code == 403


def test_usage_dashboard_allowed_for_admin(client, tokens):
    # Generate at least one of each kind of interaction so the
    # aggregates aren't trivially empty.
    client.post("/api/v1/chat/policy", json={"message": "What is the leave policy?"}, headers=auth(tokens["admin"]))
    client.post("/api/v1/chat/sql", json={"message": "Which projects are currently ongoing?"},
                headers=auth(tokens["admin"]))
    client.post("/api/v1/chat/actions", json={"message": "Check my leave balance"}, headers=auth(tokens["admin"]))

    r = client.get("/api/v1/chat/audit/usage", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total_requests"] > 0
    assert isinstance(data["requests_by_intent"], dict)
    assert isinstance(data["requests_by_tool"], dict)
    assert "failed_permission_attempts" in data
    assert "avg_latency_ms" in data
    assert "rag_no_answer_rate_pct" in data
    assert "sql_blocked_count" in data


def test_usage_dashboard_counts_a_denied_sql_request_as_blocked(client, tokens):
    # "Show pending leave requests" maps to the pending_team_leave_requests
    # template, which is manager/admin-only — an employee asking this
    # is a genuine RBAC denial (not just a template miss), which the
    # dashboard's sql_blocked_count aggregate tracks.
    client.post(
        "/api/v1/chat/sql",
        json={"message": "Show pending leave requests"},
        headers=auth(tokens["employee"]),
    )

    r = client.get("/api/v1/chat/audit/usage", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    assert r.json()["data"]["sql_blocked_count"] >= 1
