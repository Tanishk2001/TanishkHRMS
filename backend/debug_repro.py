"""
Quick manual repro of the exact sequence that hung in pytest:
  1. admin fires chat/policy, chat/sql, chat/actions (matches
     test_usage_dashboard_allowed_for_admin)
  2. employee immediately fires chat/sql with a manager-only question
     (matches test_usage_dashboard_counts_a_denied_sql_request_as_blocked,
     the exact test that hung)

Run this AFTER starting the server manually in another terminal:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

Usage:
    python debug_repro.py
"""
import time
import httpx

BASE = "http://127.0.0.1:8001"


def login(email, password):
    r = httpx.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def call(label, token, path, message, timeout=15):
    start = time.time()
    try:
        r = httpx.post(f"{BASE}{path}", json={"message": message},
                        headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
        elapsed = time.time() - start
        print(f"[{elapsed:5.2f}s] {label}: HTTP {r.status_code}")
    except httpx.ReadTimeout:
        elapsed = time.time() - start
        print(f"[{elapsed:5.2f}s] {label}: TIMED OUT (this is the hang reproducing)")


print("Logging in...")
admin_token = login("admin@novaworks.com", "admin123")
employee_token = login("employee@novaworks.com", "employee123")

print("\nSimulating action-agent self-referential call volume (test_actions.py did ~10 of these)...")
for i in range(15):
    call(f"action-agent call #{i+1}", admin_token, "/api/v1/chat/actions", "Check my leave balance", timeout=15)

print("\nFiring the admin sequence (policy, sql, actions)...")
call("admin policy", admin_token, "/api/v1/chat/policy", "What is the leave policy?")
call("admin sql", admin_token, "/api/v1/chat/sql", "Which projects are currently ongoing?")
call("admin actions", admin_token, "/api/v1/chat/actions", "Check my leave balance")

print("\nFiring the employee denied-SQL request (this is the one that hung)...")
call("employee denied sql", employee_token, "/api/v1/chat/sql", "Show pending leave requests")

print("\nDone. If every line above shows a fast HTTP status (not TIMED OUT), the connection-churn fix worked.")
