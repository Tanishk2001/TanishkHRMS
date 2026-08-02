from tests.conftest import auth


def _get_priya_id(client, admin_token) -> int:
    directory = client.get("/api/v1/employees", headers=auth(admin_token)).json()
    return next(e["id"] for e in directory if e["name"] == "Priya Dev")


def test_list_assets_admin_sees_seeded_inventory(client, tokens):
    r = client.get("/api/v1/assets", headers=auth(tokens["admin"]))
    assert r.status_code == 200
    tags = {a["asset_tag"] for a in r.json()}
    assert "LT-1001" in tags
    # seeded holder is correctly resolved
    laptop1 = next(a for a in r.json() if a["asset_tag"] == "LT-1001")
    assert laptop1["current_holder_name"] == "Employee User"
    assert laptop1["status"] == "ASSIGNED"


def test_employee_cannot_list_full_inventory(client, tokens):
    r = client.get("/api/v1/assets", headers=auth(tokens["employee"]))
    assert r.status_code == 403


def test_my_assets_scoped_to_self(client, tokens):
    r = client.get("/api/v1/assets/me", headers=auth(tokens["employee"]))
    assert r.status_code == 200
    tags = {a["asset_tag"] for a in r.json()}
    assert tags == {"LT-1001"}  # only the one seeded, currently-held asset


def test_only_admin_can_create_asset(client, tokens):
    r = client.post("/api/v1/assets", json={"asset_tag": "TEST-001", "category": "LAPTOP", "name": "Test Laptop"},
                     headers=auth(tokens["manager"]))
    assert r.status_code == 403

    r = client.post("/api/v1/assets", json={"asset_tag": "TEST-001", "category": "LAPTOP", "name": "Test Laptop"},
                     headers=auth(tokens["admin"]))
    assert r.status_code == 201


def test_duplicate_asset_tag_rejected(client, tokens):
    client.post("/api/v1/assets", json={"asset_tag": "DUP-001", "category": "MOUSE", "name": "Mouse A"},
                headers=auth(tokens["admin"]))
    r = client.post("/api/v1/assets", json={"asset_tag": "DUP-001", "category": "MOUSE", "name": "Mouse B"},
                     headers=auth(tokens["admin"]))
    assert r.status_code == 422


def test_full_issue_return_lifecycle(client, tokens):
    priya_id = _get_priya_id(client, tokens["admin"])

    created = client.post("/api/v1/assets", json={"asset_tag": "LC-9001", "category": "LAPTOP", "name": "Lifecycle Test"},
                           headers=auth(tokens["admin"])).json()
    asset_id = created["id"]
    assert created["status"] == "AVAILABLE"

    # issue
    r = client.post(f"/api/v1/assets/{asset_id}/issue",
                     json={"employee_id": priya_id, "condition_on_issue": "NEW"},
                     headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert r.json()["status"] == "ASSIGNED"

    # double-issue rejected
    r = client.post(f"/api/v1/assets/{asset_id}/issue", json={"employee_id": priya_id}, headers=auth(tokens["manager"]))
    assert r.status_code == 422

    # employee cannot issue/return
    r = client.post(f"/api/v1/assets/{asset_id}/return", json={"condition_on_return": "GOOD"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 403

    # return, good condition -> back to AVAILABLE
    r = client.post(f"/api/v1/assets/{asset_id}/return", json={"condition_on_return": "GOOD"},
                     headers=auth(tokens["manager"]))
    assert r.status_code == 200
    assert r.json()["status"] == "AVAILABLE"

    # double-return rejected
    r = client.post(f"/api/v1/assets/{asset_id}/return", json={"condition_on_return": "GOOD"},
                     headers=auth(tokens["manager"]))
    assert r.status_code == 422

    # history shows exactly one closed assignment
    r = client.get(f"/api/v1/assets/{asset_id}/history", headers=auth(tokens["admin"]))
    history = r.json()
    assert len(history) == 1
    assert history[0]["employee_name"] == "Priya Dev"
    assert history[0]["returned_at"] is not None


def test_damaged_return_flips_status_to_in_repair(client, tokens):
    priya_id = _get_priya_id(client, tokens["admin"])
    created = client.post("/api/v1/assets", json={"asset_tag": "DMG-9001", "category": "LAPTOP", "name": "Damage Test"},
                           headers=auth(tokens["admin"])).json()
    asset_id = created["id"]

    client.post(f"/api/v1/assets/{asset_id}/issue", json={"employee_id": priya_id}, headers=auth(tokens["manager"]))
    r = client.post(f"/api/v1/assets/{asset_id}/return", json={"condition_on_return": "DAMAGED", "notes": "cracked"},
                     headers=auth(tokens["manager"]))
    assert r.json()["status"] == "IN_REPAIR"


def test_returning_never_issued_asset_is_rejected(client, tokens):
    created = client.post("/api/v1/assets", json={"asset_tag": "NEV-9001", "category": "MOUSE", "name": "Never Issued"},
                           headers=auth(tokens["admin"])).json()
    r = client.post(f"/api/v1/assets/{created['id']}/return", json={"condition_on_return": "GOOD"},
                     headers=auth(tokens["manager"]))
    assert r.status_code == 422


# --- SQL agent integration ---

def test_sql_agent_my_assets(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "What assets do I have?"}, headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    tags = {row["asset_tag"] for row in body["data"]["rows"]}
    assert "LT-1001" in tags


def test_sql_agent_available_assets(client, tokens):
    r = client.post("/api/v1/chat/sql", json={"message": "Show me available assets"}, headers=auth(tokens["employee"]))
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["rows"]) >= 1
    for row in body["data"]["rows"]:
        assert "asset_tag" in row
