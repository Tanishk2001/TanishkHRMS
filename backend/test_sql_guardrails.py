from app.services.ai.sql_guardrails import validate_sql, SQLValidationError

MALICIOUS = [
    "DROP TABLE employees;",
    "DELETE FROM leave_requests;",
    "UPDATE employees SET role='ADMIN' WHERE id=1;",
    "INSERT INTO employees (name) VALUES ('hacker');",
    "SELECT * FROM employees; DROP TABLE employees;",
    "SELECT name FROM employees WHERE 1=1 -- ' OR 1=1",
    "SELECT hashed_password FROM employees",
    "SELECT bank_account_number, pan_number FROM employees",
    "PRAGMA table_info(employees);",
    "SELECT * FROM sqlite_master",
]

SAFE = [
    "SELECT name, job_title FROM employees WHERE department_id = 1",
    "SELECT p.name FROM projects p WHERE p.status = 'ONGOING'",
]

print("=== Testing malicious/unsafe SQL is blocked ===")
for sql in MALICIOUS:
    try:
        validate_sql(sql)
        print(f"FAIL (not blocked!): {sql}")
    except SQLValidationError as e:
        print(f"OK - blocked: {sql!r:60s} -> {e.message}")

print("\n=== Testing safe SQL passes and gets row-limited ===")
for sql in SAFE:
    try:
        result = validate_sql(sql)
        assert "LIMIT" in result.upper()
        print(f"OK - allowed: {sql!r} -> {result.strip()}")
    except SQLValidationError as e:
        print(f"FAIL (blocked safe query!): {sql} -> {e.message}")

print("\nGUARDRAIL UNIT TESTS COMPLETE")
