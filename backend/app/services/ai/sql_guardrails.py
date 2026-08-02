"""
SQL Agent safety layer.

Every piece of SQL — whether it came from a template or an LLM — must
pass through `validate_sql()` before execution. This is the single
choke point that enforces: read-only, single-statement, no forbidden
keywords, no forbidden/sensitive columns, and a hard row limit.
"""
from __future__ import annotations

import re

import sqlparse
from sqlparse.sql import Statement

from app.core.config import get_settings

settings = get_settings()

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "truncate", "pragma", "attach", "detach", "grant", "revoke", "vacuum",
    "exec", "execute", "call",
}

FORBIDDEN_COLUMNS = {
    "hashed_password",
    "bank_account_number",
    "bank_account_name",
    "bank_branch",
    "bank_ifsc",
    "pan_number",
    "pan_name",
    "pan_dob",
    "date_of_birth",
    "current_salary_usd",
    "profile_photo_path",
    "profile_photo_mime",
}

ALLOWED_TABLES = {
    "employees", "projects", "employee_projects", "departments",
    "skills", "employee_skills", "leave_balances", "leave_requests", "tickets",
    "attendance_records", "assets", "asset_assignments", "exit_requests",
    "polls", "poll_options", "poll_votes", "kudos", "time_entries",
}


class SQLValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _statements(sql: str) -> list[Statement]:
    return [s for s in sqlparse.parse(sql) if str(s).strip()]


def validate_sql(sql: str) -> str:
    """Raises SQLValidationError if unsafe. Returns a normalized,
    row-limited version of the SQL if it passes."""
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL was generated.")

    stmts = _statements(sql)
    if len(stmts) != 1:
        raise SQLValidationError("Only a single SQL statement is allowed per request.")

    stmt = stmts[0]
    stmt_type = stmt.get_type()
    if stmt_type != "SELECT":
        raise SQLValidationError("Only read-only SELECT queries are allowed.")

    lowered = sql.lower()

    # forbidden keywords (word-boundary match to avoid false positives like "created_at")
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lowered):
            raise SQLValidationError(f"Query contains a disallowed operation: {kw.upper()}.")

    # forbidden / sensitive columns
    for col in FORBIDDEN_COLUMNS:
        if re.search(rf"\b{col}\b", lowered):
            raise SQLValidationError("Query references a restricted field that cannot be exposed via chat.")

    # block comments (common injection technique to hide follow-on statements)
    if "--" in sql or "/*" in sql:
        raise SQLValidationError("SQL comments are not permitted in generated queries.")

    # only known tables referenced (best-effort check via FROM/JOIN tokens)
    referenced_tables = set(re.findall(r"(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered))
    unknown = referenced_tables - ALLOWED_TABLES
    if unknown:
        raise SQLValidationError(f"Query references unrecognized or disallowed table(s): {', '.join(unknown)}.")

    # enforce row limit
    if re.search(r"\blimit\b", lowered):
        sql = re.sub(r"limit\s+\d+", f"LIMIT {settings.SQL_AGENT_MAX_ROWS}", sql, flags=re.IGNORECASE)
    else:
        sql = sql.rstrip().rstrip(";") + f" LIMIT {settings.SQL_AGENT_MAX_ROWS}"

    return sql
