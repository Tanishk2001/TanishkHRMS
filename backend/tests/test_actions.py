import datetime as dt

from tests.conftest import auth


def _future_date(days: int) -> str:
    d = dt.date.today() + dt.timedelta(days=days)
    return f"{d.strftime('%B')} {d.day}"


def test_apply_leave_with_past_date_is_rejected_by_the_real_endpoint(client, tokens):
    r = client.post("/api/v1/chat/actions",
                     json={"message": "Apply sick leave from May 6 to May 7 because I have fever."},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["data"]["status"] == "ERROR"


def test_apply_leave_with_future_date_succeeds(client, tokens):
    start = _future_date(20)
    end = _future_date(21)
    r = client.post("/api/v1/chat/actions",
                     json={"message": f"Apply sick leave from {start} to {end} because I have fever."},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "SUCCESS"
    assert "submitted" in body["data"]["answer"].lower()
    # Clean up: resolve it immediately so it doesn't linger PENDING and
    # create ambiguity for the name-matching tests further down, which
    # each expect exactly one pending request to resolve against.
    _approve_via_manager(client, tokens["manager"], "Employee User")


def test_check_leave_balance(client, tokens):
    r = client.post("/api/v1/chat/actions", json={"message": "Check my leave balance"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert "SICK" in body["data"]["answer"]


def test_create_ticket(client, tokens):
    r = client.post("/api/v1/chat/actions",
                     json={"message": "Create a high-priority IT ticket for VPN not working."},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert "ticket" in body["data"]["answer"].lower()


def test_employee_cannot_approve_leave(client, tokens):
    r = client.post("/api/v1/chat/actions", json={"message": "Approve Rahul's leave request."},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["data"]["status"] == "DENIED"
    assert "permission" in body["data"]["answer"].lower()
    # must not confirm or deny the request's existence
    assert "found" not in body["data"]["answer"].lower()


def test_announcement_requires_confirmation_then_posts(client, tokens):
    r = client.post("/api/v1/chat/actions",
                     json={"message": "Create an announcement that Friday's townhall is moved to 5 PM."},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["data"]["status"] == "NEEDS_CONFIRMATION"
    pending = body["data"]["pending_action"]

    r2 = client.post("/api/v1/chat/actions",
                      json={"message": "yes", "confirm": True, "pending_action": pending},
                      headers=auth(tokens["manager"]))
    body2 = r2.json()
    assert body2["data"]["status"] == "SUCCESS"
    assert "posted" in body2["data"]["answer"].lower()


# --- Approve/reject leave name matching: several phrasings ---

def _apply_future_leave(client, token, days_offset: int, leave_type: str = "casual") -> None:
    start = _future_date(days_offset)
    end = _future_date(days_offset + 1)
    r = client.post(
        "/api/v1/chat/actions",
        json={"message": f"Apply {leave_type} leave from {start} to {end} because of personal work."},
        headers=auth(token),
    )
    assert r.json()["data"]["status"] == "SUCCESS"


def _approve_via_manager(client, manager_token, employee_name: str) -> None:
    """Resolves and approves whatever single pending request currently
    exists for this employee — used to consume a leave request right
    after a test creates it, so it can't cause 'found more than one
    pending request' ambiguity in a later test."""
    r = client.post("/api/v1/chat/actions", json={"message": f"Approve {employee_name}'s leave request."},
                     headers=auth(manager_token))
    body = r.json()
    if body["data"]["status"] != "NEEDS_CONFIRMATION":
        return  # nothing pending — already clean
    pending = body["data"]["pending_action"]
    client.post("/api/v1/chat/actions",
                json={"message": "yes", "confirm": True, "pending_action": pending},
                headers=auth(manager_token))


def test_approve_leave_possessive_phrasing(client, tokens):
    _apply_future_leave(client, tokens["employee"], 30)
    r = client.post("/api/v1/chat/actions", json={"message": "Approve Employee User's leave request."},
                     headers=auth(tokens["manager"]))
    assert r.json()["data"]["status"] == "NEEDS_CONFIRMATION"
    _approve_via_manager(client, tokens["manager"], "Employee User")


def test_approve_leave_prepositional_phrasing(client, tokens):
    _apply_future_leave(client, tokens["employee"], 32)
    r = client.post("/api/v1/chat/actions",
                     json={"message": "Please approve the leave request for Employee User."},
                     headers=auth(tokens["manager"]))
    assert r.json()["data"]["status"] == "NEEDS_CONFIRMATION"
    _approve_via_manager(client, tokens["manager"], "Employee User")


def test_approve_leave_non_possessive_phrasing(client, tokens):
    _apply_future_leave(client, tokens["employee"], 34)
    r = client.post("/api/v1/chat/actions", json={"message": "approve Employee User leave"},
                     headers=auth(tokens["manager"]))
    assert r.json()["data"]["status"] == "NEEDS_CONFIRMATION"
    _approve_via_manager(client, tokens["manager"], "Employee User")


def test_approve_leave_no_pending_request_gives_clean_refusal(client, tokens):
    r = client.post("/api/v1/chat/actions", json={"message": "Approve Priya Dev's leave request."},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["data"]["status"] == "ERROR"
    assert "couldn't find" in body["data"]["answer"].lower()
