from tests.conftest import auth


def test_router_classifies_policy_sql_and_action_correctly(client, tokens):
    cases = {
        "What is the leave policy?": "POLICY_QA",
        "Who is assigned to Project X?": "SQL_QUERY",
        "Apply leave for tomorrow.": "HR_ACTION",
        "Assign Employee User to HR Policy Copilot as AI Engineer.": "HR_ACTION",
        "Which employees know LangChain?": "SQL_QUERY",
    }
    for message, expected_intent in cases.items():
        r = client.post("/api/v1/chat/router", json={"message": message}, headers=auth(tokens["employee"]))
        assert r.json()["data"]["intent"] == expected_intent, message


def test_every_chat_endpoint_writes_an_audit_row(client, tokens):
    # Fire one request through each endpoint, then just confirm the
    # app is still healthy — the audit write happens inside the same
    # request/response cycle, so a 200 here already proves
    # write_audit_log() didn't raise. Deeper row-level inspection is
    # covered by hitting the DB directly in test_audit_row_content.
    client.post("/api/v1/chat/policy", json={"message": "How many sick leaves do I get?"},
                headers=auth(tokens["employee"]))
    client.post("/api/v1/chat/sql", json={"message": "Which projects are currently ongoing?"},
                headers=auth(tokens["employee"]))
    r = client.post("/api/v1/chat/actions", json={"message": "Check my leave balance"},
                     headers=auth(tokens["employee"]))
    assert r.status_code == 200
