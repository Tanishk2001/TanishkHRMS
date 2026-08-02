"""
Pure unit tests for the SQL safety layer — no server, no DB, no
network. Every malicious/unsafe query the assignment's security
prompts mention gets its own assertion.
"""
import pytest

from app.services.ai.sql_guardrails import validate_sql, SQLValidationError

MALICIOUS_QUERIES = [
    "DROP TABLE employees;",
    "DELETE FROM leave_requests;",
    "UPDATE employees SET role='ADMIN' WHERE id=1;",
    "INSERT INTO employees (name) VALUES ('hacker');",
    "SELECT * FROM employees; DROP TABLE employees;",
    "SELECT name FROM employees WHERE 1=1 -- ' OR 1=1",
    "SELECT hashed_password FROM employees",
    "SELECT bank_account_number, pan_number FROM employees",
    "SELECT current_salary_usd FROM employees",
    "PRAGMA table_info(employees);",
    "SELECT * FROM sqlite_master",
]


@pytest.mark.parametrize("sql", MALICIOUS_QUERIES)
def test_malicious_sql_is_blocked(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


SAFE_QUERIES = [
    "SELECT name, job_title FROM employees WHERE department_id = 1",
    "SELECT p.name FROM projects p WHERE p.status = 'ONGOING'",
]


@pytest.mark.parametrize("sql", SAFE_QUERIES)
def test_safe_sql_is_allowed_and_row_limited(sql):
    result = validate_sql(sql)
    assert "LIMIT" in result.upper()


def test_row_limit_is_enforced_even_if_caller_asks_for_more():
    result = validate_sql("SELECT name FROM employees LIMIT 999999")
    assert "LIMIT 200" in result
