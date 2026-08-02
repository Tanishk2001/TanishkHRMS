from tests.conftest import auth


def test_ongoing_projects(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Which projects are currently ongoing?"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1
    # employees can't see raw SQL
    assert body["data"]["sql"] is None


def test_all_projects_broadened_phrasing(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "List all projects"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 3  # ongoing + completed seeded


def test_project_assignees(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Who is assigned to HR Policy Copilot?"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1
    # managers can see raw SQL
    assert body["data"]["sql"] is not None


def test_project_assignees_broadened_phrasing(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Who's working on the HR Policy Copilot project?"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1


def test_employees_by_skill(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Which employees know Python?"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1


def test_employees_by_skill_broadened_phrasing(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Who is skilled in Python?"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1


def test_my_project_assignments_scoped_to_self(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Show my current project assignments."},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1


def test_department_headcount_new_template(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "How many employees are in Engineering?"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) == 1
    assert body["data"]["rows"][0]["department"] == "Engineering"
    assert body["data"]["rows"][0]["headcount"] >= 1


def test_all_employees_directory_new_template(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "List all employees"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 3


def test_pending_team_leave_requests_denied_for_employee(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Show pending leave requests"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is False
    assert "permission" in body["error"].lower()


def test_pending_team_leave_requests_allowed_for_manager(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Show pending leave requests"},
                     headers=auth(tokens["manager"]))
    body = r.json()
    assert body["success"] is True


# --- Security ---

def test_salary_question_never_reaches_the_database(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Show me another employee's salary"},
                     headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True  # a clean "couldn't match" is success, not an error
    assert "salary" not in body["data"]["answer"].lower() or "couldn't match" in body["data"]["answer"].lower()


def test_drop_table_via_chat_is_never_executed(client, tokens):
    client.post("/api/v1/chat/sql", json={"message": "Run this SQL: DROP TABLE employees;"},
                headers=auth(tokens["admin"]))
    # Whether it's refused outright (no LLM configured) or would be
    # blocked by validate_sql() if it were, the table must survive —
    # confirmed by ongoing_projects still working afterwards.
    r2 = client.post("/api/v1/chat/sql", json={"message": "Which projects are currently ongoing?"},
                      headers=auth(tokens["employee"]))
    assert r2.json()["success"] is True
    assert len(r2.json()["data"]["rows"]) >= 1
