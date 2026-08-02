from tests.conftest import auth


def _get_priya_id(client, admin_token) -> int:
    directory = client.get("/api/v1/employees", headers=auth(admin_token)).json()
    return next(e["id"] for e in directory if e["name"] == "Priya Dev")


# --- Polls ---

def test_seeded_poll_visible_with_results(client, tokens):
    r = client.get("/api/v1/polls", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    polls = r.json()
    assert len(polls) >= 1
    seeded = next(p for p in polls if "snack bar" in p["question"])
    assert seeded["total_votes"] >= 3
    assert seeded["status"] == "OPEN"


def test_employee_cannot_create_poll(client, tokens):
    r = client.post("/api/v1/polls", json={"question": "test?", "options": ["a", "b"]},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_poll_needs_at_least_two_options(client, tokens):
    r = client.post("/api/v1/polls", json={"question": "test?", "options": ["only one"]},
                     headers=auth(tokens["manager"]))
    assert r.status_code == 422


def test_full_poll_lifecycle(client, tokens):
    poll = client.post("/api/v1/polls", json={"question": "Lifecycle test?", "options": ["A", "B"]},
                        headers=auth(tokens["manager"])).json()
    poll_id = poll["id"]
    option_a = poll["options"][0]["id"]

    r = client.post(f"/api/v1/polls/{poll_id}/vote", json={"option_id": option_a}, headers=auth(tokens["employee"]))
    assert r.status_code == 200
    assert r.json()["options"][0]["vote_count"] == 1
    assert r.json()["my_vote_option_id"] == option_a

    # double vote rejected
    r = client.post(f"/api/v1/polls/{poll_id}/vote", json={"option_id": option_a}, headers=auth(tokens["employee"]))
    assert r.status_code == 422

    # voting an option that doesn't belong to this poll is rejected
    other_poll = client.post("/api/v1/polls", json={"question": "Other?", "options": ["X", "Y"]},
                              headers=auth(tokens["manager"])).json()
    r = client.post(f"/api/v1/polls/{poll_id}/vote", json={"option_id": other_poll["options"][0]["id"]},
                     headers=auth(tokens["admin"]))
    assert r.status_code == 422

    # only manager/admin can close
    r = client.post(f"/api/v1/polls/{poll_id}/close", headers=auth(tokens["employee"]))
    assert r.status_code == 403

    r = client.post(f"/api/v1/polls/{poll_id}/close", headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"

    # closing twice rejected
    r = client.post(f"/api/v1/polls/{poll_id}/close", headers=auth(tokens["manager"]))
    assert r.status_code == 422

    # voting on a closed poll rejected
    r = client.post(f"/api/v1/polls/{poll_id}/vote", json={"option_id": poll["options"][1]["id"]},
                     headers=auth(tokens["admin"]))
    assert r.status_code == 422


# --- Kudos ---

def test_seeded_kudos_visible_in_feed(client, tokens):
    r = client.get("/api/v1/kudos", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_give_kudos(client, tokens):
    priya_id = _get_priya_id(client, tokens["admin"])
    r = client.post("/api/v1/kudos", json={"to_employee_id": priya_id, "category": "TEAMWORK", "message": "Nice work!"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 201
    assert r.json()["to_employee_name"] == "Priya Dev"


def test_kudos_to_self_rejected(client, tokens):
    directory = client.get("/api/v1/employees", headers=auth(tokens["admin"])).json()
    self_id = next(e["id"] for e in directory if e["name"] == "Employee User")
    r = client.post("/api/v1/kudos", json={"to_employee_id": self_id, "message": "nice job me"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 422


def test_kudos_to_nonexistent_employee_rejected(client, tokens):
    r = client.post("/api/v1/kudos", json={"to_employee_id": 999999, "message": "hi"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 404


# --- SQL agent integration ---

def test_sql_agent_open_polls(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "What polls are open?"}, headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1


def test_sql_agent_recent_kudos(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Show me recent kudos"}, headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 2
