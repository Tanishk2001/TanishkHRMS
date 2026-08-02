import re
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, CurrentUser
from app.db.database import get_db
from app.schemas.chat import (
    ChatMessageRequest, ChatActionRequest, ChatEnvelope,
    AIAuditLogOut, AIUsageStatsOut,
)
from app.services.ai import policy_rag, sql_agent, action_agent, audit, permissions

router = APIRouter(prefix="/api/v1/chat", tags=["ai-chat"])


@router.post("/policy", response_model=ChatEnvelope)
def chat_policy(
    payload: ChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    result = policy_rag.answer_policy_question(db, payload.message)

    audit.write_audit_log(
        db, user_id=user.id, role=user.role, message=payload.message,
        intent="POLICY_QA", tool_name="policy_rag",
        action_status="SUCCESS" if result.grounded else "NO_ANSWER",
        latency_ms=int((time.perf_counter() - started) * 1000),
    )

    return ChatEnvelope(
        success=True,
        data={
            "answer": result.answer,
            "sources": [s.__dict__ for s in result.sources],
        },
    )


@router.post("/sql", response_model=ChatEnvelope)
def chat_sql(
    payload: ChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    result = sql_agent.answer_sql_question(db, user, payload.message)

    audit.write_audit_log(
        db, user_id=user.id, role=user.role, message=payload.message,
        intent="SQL_QUERY", tool_name="sql_agent",
        action_status="DENIED" if result.denied else "SUCCESS",
        latency_ms=int((time.perf_counter() - started) * 1000),
    )

    return ChatEnvelope(
        success=not result.denied,
        data={"answer": result.answer, "sql": result.sql, "rows": result.rows} if not result.denied else None,
        error=result.answer if result.denied else None,
    )


@router.post("/actions", response_model=ChatEnvelope)
async def chat_actions(
    payload: ChatActionRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    result = await action_agent.handle_action(
        db, user, payload.message, confirm=payload.confirm, pending_action=payload.pending_action,
    )

    audit.write_audit_log(
        db, user_id=user.id, role=user.role, message=payload.message,
        intent=result.intent, tool_name=result.tool_name,
        action_status=result.status, records_accessed=result.records_accessed,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )

    return ChatEnvelope(
        success=result.status in ("SUCCESS", "NEEDS_CONFIRMATION"),
        data={
            "answer": result.answer,
            "intent": result.intent,
            "status": result.status,
            "needs_confirmation": result.needs_confirmation,
            "pending_action": result.pending_action,
        },
        error=result.answer if result.status in ("DENIED", "ERROR") else None,
    )


@router.post("/router", response_model=ChatEnvelope)
def chat_router(
    payload: ChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lightweight rule-based intent router — classifies which
    sub-system a message belongs to without executing anything.

    Ordering matters here: a question like "Who is assigned to Project
    X?" must route to SQL_QUERY even though it contains "assign",
    which is otherwise an HR_ACTION trigger word. We detect that case
    up front by checking whether the message is phrased as a
    who/which/show/find *question* rather than an imperative command
    (e.g. "Assign Employee User to Project X" has no question word and
    correctly falls through to HR_ACTION below)."""
    lowered = payload.message.lower()

    # An imperative HR action verb at the very start of the message is
    # an unambiguous signal — checked first so it can't be overridden
    # by an incidental keyword elsewhere in the message (e.g. "Assign
    # Employee User to HR Policy Copilot" contains the word "policy"
    # as part of a project name, not as a policy question).
    starts_with_action_verb = bool(re.match(r"^(apply|approve|reject|create|assign)\b", lowered))

    is_data_question = bool(re.match(r"^(who|which|show|find)\b", lowered)) or bool(
        re.search(r"\b(who|which)\b.*\bassigned\b", lowered)
    )

    if starts_with_action_verb:
        intent, confidence, reason = "HR_ACTION", 0.85, "Message opens with an imperative HR action verb."
    elif is_data_question:
        intent, confidence, reason = "SQL_QUERY", 0.8, "Message asks a who/which/show/find question about data."
    elif any(w in lowered for w in ("policy", "leave policy", "wfh", "work from home", "sick leave", "late")):
        intent, confidence, reason = "POLICY_QA", 0.8, "Message asks about an HR policy/rule."
    elif any(w in lowered for w in ("apply", "create ticket", "approve", "assign", "announcement")):
        intent, confidence, reason = "HR_ACTION", 0.7, "Message requests an HR task to be performed."
    elif any(w in lowered for w in ("who", "which employees", "project", "skill", "assigned")):
        intent, confidence, reason = "SQL_QUERY", 0.6, "Message asks for data about people/projects."
    else:
        intent, confidence, reason = "UNKNOWN", 0.3, "Could not confidently classify the message."

    audit.write_audit_log(
        db, user_id=user.id, role=user.role, message=payload.message,
        intent=intent, tool_name="router", action_status="SUCCESS",
    )

    return ChatEnvelope(success=True, data={"intent": intent, "confidence": confidence, "reason": reason})


@router.get("/audit/recent", response_model=ChatEnvelope)
def recent_ai_actions(
    limit: int = 10,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Self-scoped AI activity history for the "Recent AI Actions"
    panel — every role sees only their own past requests, mirroring
    the same self/team/all scoping used everywhere else in the AI
    layer. This does not require its own audit-write: reading your
    own history is not itself an action worth logging."""
    logs = audit.recent_logs_for_user(db, user_id=user.id, limit=min(limit, 50))
    return ChatEnvelope(
        success=True,
        data={
            "logs": [
                AIAuditLogOut(
                    id=log.id,
                    message=log.message,
                    intent=log.intent,
                    tool_name=log.tool_name,
                    action_status=log.action_status,
                    created_at=log.created_at.isoformat(),
                ).model_dump()
                for log in logs
            ]
        },
    )


@router.get("/audit/usage", response_model=ChatEnvelope)
def ai_usage_dashboard(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Company-wide AI usage metrics for admins (bonus #8) — total
    requests, intent/tool breakdowns, denied-permission count, average
    latency, RAG no-answer rate, SQL blocked-query count."""
    if not permissions.can_view_ai_usage_dashboard(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view the AI usage dashboard.",
        )

    stats = audit.usage_stats(db)
    return ChatEnvelope(success=True, data=AIUsageStatsOut(**stats.__dict__).model_dump())
