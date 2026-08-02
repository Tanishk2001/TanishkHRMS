from tests.conftest import auth


def test_only_admin_can_create_employee(client, tokens):
    for role in ("employee", "manager"):
        r = client.post(
            "/api/v1/employees",
            json={"name": "New Hire", "email": f"nohire-{role}@novaworks.com", "password": "pass1234"},
            headers=auth(tokens[role]),
        )
        assert r.status_code == 403


def test_admin_can_create_employee(client, tokens):
    r = client.post(
        "/api/v1/employees",
        json={
            "name": "Jordan New",
            "email": "jordan.new@novaworks.com",
            "password": "welcome123",
            "role": "EMPLOYEE",
            "job_title": "QA Engineer",
        },
        headers=auth(tokens["admin"]),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Jordan New"
    assert body["role"] == "EMPLOYEE"

    # shows up in the directory immediately
    directory = client.get("/api/v1/employees", headers=auth(tokens["admin"])).json()
    assert any(e["name"] == "Jordan New" for e in directory)


def test_new_employee_can_log_in_with_the_password_they_were_given(client, tokens):
    client.post(
        "/api/v1/employees",
        json={"name": "Login Check", "email": "login.check@novaworks.com", "password": "checkme123"},
        headers=auth(tokens["admin"]),
    )
    r = client.post("/api/v1/auth/login", json={"email": "login.check@novaworks.com", "password": "checkme123"})
    assert r.status_code == 200
    assert r.json()["role"] == "EMPLOYEE"


def test_duplicate_email_rejected(client, tokens):
    r = client.post(
        "/api/v1/employees",
        json={"name": "Duplicate", "email": "employee@novaworks.com", "password": "pass1234"},
        headers=auth(tokens["admin"]),
    )
    assert r.status_code == 422


def test_invalid_role_rejected(client, tokens):
    r = client.post(
        "/api/v1/employees",
        json={"name": "Bad Role", "email": "badrole@novaworks.com", "password": "pass1234", "role": "SUPERUSER"},
        headers=auth(tokens["admin"]),
    )
    assert r.status_code == 422


def test_nonexistent_department_rejected(client, tokens):
    r = client.post(
        "/api/v1/employees",
        json={"name": "Ghost Dept", "email": "ghostdept@novaworks.com", "password": "pass1234", "department_id": 9999},
        headers=auth(tokens["admin"]),
    )
    assert r.status_code == 404


def test_list_departments_available_to_any_role(client, tokens):
    for role in ("employee", "manager", "admin"):
        r = client.get("/api/v1/employees/departments", headers=auth(tokens[role]))
        assert r.status_code == 200
        assert len(r.json()) > 0
        assert "name" in r.json()[0]
