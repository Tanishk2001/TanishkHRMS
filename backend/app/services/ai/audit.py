"""
AI audit logging.

Every AI interaction across all three agents (policy, sql, actions)
should call `write_audit_log` exactly once. Never pass secrets, full
JWTs, passwords, bank numbers, or PAN numbers into `records_accessed`
or `message` — only IDs and short status metadata.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_audit_log import AIAuditLog


def write_audit_log(
    db: Session,
    *,
    user_id: int,
    role: str,
    message: str,
    intent: str | None,
    tool_name: str | None,
    action_status: str,
    records_accessed: list[int] | None = None,
    latency_ms: int | None = None,
) -> None:
    log = AIAuditLog(
        user_id=user_id,
        role=role,
        message=message[:2000],
        intent=intent,
        tool_name=tool_name,
        action_status=action_status,
        records_accessed=",".join(str(r) for r in records_accessed) if records_accessed else None,
        latency_ms=latency_ms,
    )
    db.add(log)
    db.commit()


def recent_logs_for_user(db: Session, *, user_id: int, limit: int = 10) -> list[AIAuditLog]:
    """Self-scoped history for the "Recent AI Actions" panel — every
    role can see their own past interactions, never anyone else's."""
    return (
        db.query(AIAuditLog)
        .filter(AIAuditLog.user_id == user_id)
        .order_by(AIAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )


@dataclass
class AIUsageStats:
    total_requests: int
    requests_by_intent: dict[str, int]
    requests_by_tool: dict[str, int]
    failed_permission_attempts: int
    avg_latency_ms: float | None
    rag_no_answer_count: int
    rag_no_answer_rate_pct: float | None
    sql_blocked_count: int


def usage_stats(db: Session) -> AIUsageStats:
    """Company-wide aggregates for the admin AI usage dashboard
    (bonus #8) — never scoped to a single user, so callers must gate
    this behind `permissions.can_view_ai_usage_dashboard`."""
    total_requests = db.query(func.count(AIAuditLog.id)).scalar() or 0

    intent_rows = (
        db.query(AIAuditLog.intent, func.count(AIAuditLog.id))
        .group_by(AIAuditLog.intent)
        .all()
    )
    tool_rows = (
        db.query(AIAuditLog.tool_name, func.count(AIAuditLog.id))
        .group_by(AIAuditLog.tool_name)
        .all()
    )
    failed_permission_attempts = (
        db.query(func.count(AIAuditLog.id))
        .filter(AIAuditLog.action_status == "DENIED")
        .scalar()
        or 0
    )
    avg_latency = db.query(func.avg(AIAuditLog.latency_ms)).filter(AIAuditLog.latency_ms.isnot(None)).scalar()

    policy_total = (
        db.query(func.count(AIAuditLog.id)).filter(AIAuditLog.intent == "POLICY_QA").scalar() or 0
    )
    rag_no_answer_count = (
        db.query(func.count(AIAuditLog.id))
        .filter(AIAuditLog.intent == "POLICY_QA", AIAuditLog.action_status == "NO_ANSWER")
        .scalar()
        or 0
    )
    rag_no_answer_rate = round((rag_no_answer_count / policy_total) * 100, 1) if policy_total else None

    sql_blocked_count = (
        db.query(func.count(AIAuditLog.id))
        .filter(AIAuditLog.intent == "SQL_QUERY", AIAuditLog.action_status == "DENIED")
        .scalar()
        or 0
    )

    return AIUsageStats(
        total_requests=total_requests,
        requests_by_intent={(k or "UNKNOWN"): v for k, v in intent_rows},
        requests_by_tool={(k or "unknown"): v for k, v in tool_rows},
        failed_permission_attempts=failed_permission_attempts,
        avg_latency_ms=round(avg_latency, 1) if avg_latency is not None else None,
        rag_no_answer_count=rag_no_answer_count,
        rag_no_answer_rate_pct=rag_no_answer_rate,
        sql_blocked_count=sql_blocked_count,
    )
