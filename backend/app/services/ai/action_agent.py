"""
HR Task Automation Agent.

Flow: extract intent + structured parameters from the user's message
-> permission check against services/ai/permissions.py -> for
high-impact actions, return a confirmation prompt instead of acting
immediately -> on confirmed actions, call the matching backend API
tool (never raw SQL) -> summarize the result in plain language.

The agent is intentionally stateless across turns: when a
confirmation is required, the structured `pending_action` payload is
returned to the caller and must be echoed back (with confirm=true) to
proceed. No server-side session state is required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.models.hrms import Employee, LeaveRequest
from app.services.ai import api_tools, permissions

HIGH_IMPACT_INTENTS = {
    "APPROVE_LEAVE", "REJECT_LEAVE", "ASSIGN_EMPLOYEE_TO_PROJECT",
    "CREATE_ANNOUNCEMENT", "UPDATE_TICKET",
}


@dataclass
class ActionResult:
    answer: str
    intent: str | None = None
    tool_name: str | None = None
    status: str = "SUCCESS"  # SUCCESS | DENIED | ERROR | NEEDS_CONFIRMATION
    needs_confirmation: bool = False
    pending_action: dict | None = None
    records_accessed: list[int] = field(default_factory=list)


# --- Intent extraction ------------------------------------------------

def _parse_date(text_fragment: str, base: date) -> date | None:
    text_fragment = text_fragment.strip().lower()
    if text_fragment in ("today",):
        return base
    if text_fragment in ("tomorrow",):
        return base + timedelta(days=1)
    try:
        return date_parser.parse(text_fragment, fuzzy=True, default=date_parser.parser().parse(str(base))).date()
    except Exception:
        return None


def _extract_leave_request(message: str) -> dict:
    lowered = message.lower()
    leave_type = "CASUAL"
    if "sick" in lowered:
        leave_type = "SICK"
    elif "earned" in lowered or "annual" in lowered:
        leave_type = "EARNED"
    elif "casual" in lowered:
        leave_type = "CASUAL"

    today = date.today()
    is_half_day = "half day" in lowered or "half-day" in lowered

    date_range = re.search(
        r"from\s+([a-z]+\s+\d{1,2}(?:st|nd|rd|th)?)\s+to\s+([a-z]+\s+\d{1,2}(?:st|nd|rd|th)?)",
        lowered,
    )
    start_date = end_date = None
    if date_range:
        start_date = _parse_date(date_range.group(1), today)
        end_date = _parse_date(date_range.group(2), today)
    elif "tomorrow" in lowered:
        start_date = end_date = today + timedelta(days=1)
    elif "today" in lowered:
        start_date = end_date = today

    reason_match = re.search(r"because(?: of)?\s+(.+)$", message, flags=re.IGNORECASE)
    reason = reason_match.group(1).strip().rstrip(".") if reason_match else None

    return {
        "leave_type": leave_type,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "is_half_day": is_half_day,
        "half_day_period": None,
        "reason": reason,
    }


def _extract_ticket(message: str) -> dict:
    lowered = message.lower()
    priority = "MEDIUM"
    if "high-priority" in lowered or "high priority" in lowered or "urgent" in lowered:
        priority = "HIGH"
    elif "low-priority" in lowered or "low priority" in lowered:
        priority = "LOW"

    title_match = re.search(r"ticket for\s+(.+)$", message, flags=re.IGNORECASE)
    title = title_match.group(1).strip().rstrip(".") if title_match else message.strip()

    return {"title": title[:200], "description": message.strip(), "priority": priority}


def _extract_announcement(message: str) -> dict:
    body_match = re.search(r"announcement (?:that )?(.+)$", message, flags=re.IGNORECASE)
    body = body_match.group(1).strip().rstrip(".") if body_match else message.strip()
    title = body[:80] if body else "Announcement"
    return {"title": title, "body": body}


def _resolve_pending_leave_request(db: Session, user: CurrentUser, employee_name: str | None) -> tuple[dict, str | None]:
    """Resolves a free-text employee name to exactly one PENDING leave
    request, scoped to the approver's authority (a manager only sees
    their own team's requests; an admin sees all). This is a read-only
    lookup used to prepare the action — the actual approve/reject
    mutation still goes through the existing PATCH /leaves/requests/{id}
    endpoint, never a direct write.

    Returns (extra_payload_fields, error_message). error_message is
    None on a clean single match.
    """
    if not employee_name:
        return {}, "I couldn't tell which employee this is for — could you name them, e.g. \"approve Priya Dev's leave request\"?"

    query = (
        db.query(LeaveRequest, Employee)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .filter(LeaveRequest.status == "PENDING")
        .filter(Employee.name.ilike(f"%{employee_name}%"))
    )
    if user.role == "MANAGER":
        query = query.filter(Employee.manager_id == user.id)

    matches = query.limit(6).all()

    if not matches:
        return {}, f"I couldn't find a pending leave request for {employee_name}."

    if len(matches) > 1:
        options = "; ".join(
            f"#{lr.id} {emp.name} ({lr.leave_type} {lr.start_date} to {lr.end_date})" for lr, emp in matches
        )
        return {}, f"I found more than one pending request matching \"{employee_name}\": {options}. Please specify which one, e.g. by request ID."

    leave_request, employee = matches[0]
    return {
        "leave_request_id": leave_request.id,
        "employee_name": employee.name,
        "leave_type": leave_request.leave_type,
        "start_date": leave_request.start_date.isoformat(),
        "end_date": leave_request.end_date.isoformat(),
    }, None


def classify_intent(message: str) -> str:
    lowered = message.lower()

    if re.search(r"\b(apply|request)\b.*\bleave\b", lowered):
        return "APPLY_LEAVE"
    if "leave balance" in lowered:
        return "CHECK_LEAVE_BALANCE"
    if re.search(r"\bapprove\b.*\bleave\b", lowered):
        return "APPROVE_LEAVE"
    if re.search(r"\breject\b.*\bleave\b", lowered):
        return "REJECT_LEAVE"
    if re.search(r"\bcreate\b.*\bticket\b", lowered):
        return "CREATE_TICKET"
    if re.search(r"\b(assign|update)\b.*\bticket\b", lowered):
        return "UPDATE_TICKET"
    if "ticket status" in lowered or "status of my ticket" in lowered:
        return "CHECK_TICKET_STATUS"
    if re.search(r"\bcreate\b.*\bannouncement\b", lowered):
        return "CREATE_ANNOUNCEMENT"
    if re.search(r"\bassign\b.*\bto\b.*\bproject\b", lowered):
        return "ASSIGN_EMPLOYEE_TO_PROJECT"
    if "view my project" in lowered or "my projects" in lowered:
        return "VIEW_PROJECTS"
    return "UNKNOWN"


# --- Main entry point ---------------------------------------------------

async def handle_action(
    db: Session,
    user: CurrentUser,
    message: str,
    confirm: bool = False,
    pending_action: dict | None = None,
) -> ActionResult:
    intent = pending_action.get("intent") if pending_action else classify_intent(message)

    if intent == "UNKNOWN":
        return ActionResult(
            answer="I'm not sure which HR task you want to perform. Try things like "
                   "\"apply sick leave from May 6 to May 7\" or \"create a ticket for VPN issue\".",
            intent=intent,
            status="ERROR",
        )

    # --- Permission gate (checked BEFORE any extraction/tool call) ---
    permission_map = {
        "APPROVE_LEAVE": permissions.can_approve_or_reject_leave,
        "REJECT_LEAVE": permissions.can_approve_or_reject_leave,
        "UPDATE_TICKET": permissions.can_assign_or_update_ticket,
        "CREATE_ANNOUNCEMENT": permissions.can_create_announcement,
        "ASSIGN_EMPLOYEE_TO_PROJECT": permissions.can_assign_employee_to_project,
    }
    checker = permission_map.get(intent)
    if checker and not checker(user):
        return ActionResult(
            answer="You do not have permission to perform this action.",
            intent=intent,
            status="DENIED",
        )

    if pending_action:
        payload = pending_action.get("payload", {})
    else:
        payload, build_error = _build_payload(db, user, intent, message)
        if build_error:
            return ActionResult(answer=build_error, intent=intent, status="ERROR")

    # --- High-impact actions require explicit confirmation ---
    if intent in HIGH_IMPACT_INTENTS and not confirm:
        return ActionResult(
            answer=_confirmation_prompt(intent, payload),
            intent=intent,
            status="NEEDS_CONFIRMATION",
            needs_confirmation=True,
            pending_action={"intent": intent, "payload": payload},
        )

    return await _execute(user, intent, payload)


def _extract_employee_name(message: str) -> str | None:
    """Tries several phrasings, in order of specificity, to pull the
    employee's name out of an approve/reject request. Handles
    possessive ("Priya Dev's leave"), non-possessive ("approve Priya
    Dev leave"), and prepositional ("approve the leave request for
    Priya Dev" / "...from Priya Dev" / "...of Priya Dev") forms, in
    any capitalization — the downstream DB lookup is case-insensitive
    anyway, so this doesn't need to guess capitalization correctly.

    The possessive pattern below has no literal anchor word before the
    name (unlike the others, which are anchored after "for"/"approve"
    etc.), so a plain greedy word-capture would happily swallow the
    leading verb too — e.g. matching "Approve Employee User" instead
    of "Employee User" for "Approve Employee User's leave request."
    The `\\b(?!STOPWORD\\b)` guard blocks the match from starting on a
    verb/filler word, forcing it to start at the next real word
    boundary instead.
    """
    stop = r"(?:approve|reject|please|kindly|confirm|the|this|that|his|her|their|an)"
    word = rf"\b(?:(?!{stop}\b)[A-Za-z][A-Za-z\-']*)"
    name = rf"{word}(?:\s+[A-Za-z][A-Za-z\-']*){{0,2}}"
    patterns = [
        # "Priya Dev's leave" / "Priya Dev's casual leave request"
        rf"({name})'s\s+(?:\w+\s+)?leave",
        # "leave request for/from/of Priya Dev"
        rf"leave\s+(?:request\s+)?(?:for|from|of)\s+({name})",
        # "approve/reject the leave request for/from/of Priya Dev"
        rf"(?:approve|reject)\w*\s+(?:the\s+)?leave\s+(?:request\s+)?(?:for|from|of)\s+({name})",
        # "approve/reject Priya Dev's leave" / "approve/reject Priya Dev leave" (no "for")
        rf"(?:approve|reject)\w*\s+({name})(?:'s)?\s+(?:\w+\s+)?leave",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate
    return None


def _build_payload(db: Session, user: CurrentUser, intent: str, message: str) -> tuple[dict, str | None]:
    """Returns (payload, error_message). error_message is set when the
    payload couldn't be fully/safely built (e.g. an ambiguous or
    unresolvable employee name for an approval)."""
    if intent == "APPLY_LEAVE":
        return _extract_leave_request(message), None
    if intent == "CREATE_TICKET":
        return _extract_ticket(message), None
    if intent == "CREATE_ANNOUNCEMENT":
        return _extract_announcement(message), None
    if intent in ("APPROVE_LEAVE", "REJECT_LEAVE"):
        employee_name = _extract_employee_name(message)
        resolved, error = _resolve_pending_leave_request(db, user, employee_name)
        if error:
            return {}, error
        return resolved, None
    return {}, None


def _confirmation_prompt(intent: str, payload: dict) -> str:
    if intent == "APPROVE_LEAVE":
        return (f"Confirm: approve {payload.get('employee_name', 'this employee')}'s "
                f"{payload.get('leave_type', '').lower()} leave "
                f"({payload.get('start_date')} to {payload.get('end_date')})?")
    if intent == "REJECT_LEAVE":
        return (f"Confirm: reject {payload.get('employee_name', 'this employee')}'s "
                f"{payload.get('leave_type', '').lower()} leave "
                f"({payload.get('start_date')} to {payload.get('end_date')})?")
    prompts = {
        "CREATE_ANNOUNCEMENT": f"Confirm: post the announcement \"{payload.get('title', '')}\"?",
        "ASSIGN_EMPLOYEE_TO_PROJECT": "Confirm: proceed with this project assignment?",
        "UPDATE_TICKET": "Confirm: apply this ticket update?",
    }
    return prompts.get(intent, "Confirm this action?")


async def _execute(user: CurrentUser, intent: str, payload: dict) -> ActionResult:
    try:
        if intent == "APPLY_LEAVE":
            if not payload.get("start_date") or not payload.get("end_date"):
                return ActionResult(
                    answer="I couldn't figure out the leave dates — could you give a specific date range?",
                    intent=intent, status="ERROR",
                )
            resp = await api_tools.create_leave_request(payload, user.access_token)
            if resp.status_code >= 400:
                return ActionResult(answer=_safe_error(resp), intent=intent, tool_name="create_leave_request", status="ERROR")
            data = resp.json()
            return ActionResult(
                answer=f"Your {payload['leave_type'].lower()} leave request for "
                       f"{payload['start_date']} to {payload['end_date']} has been submitted. Status: Pending approval.",
                intent=intent, tool_name="create_leave_request", status="SUCCESS",
                records_accessed=[data.get("id")] if isinstance(data, dict) and data.get("id") else [],
            )

        if intent == "CHECK_LEAVE_BALANCE":
            resp = await api_tools.get_leave_balance(user.access_token)
            if resp.status_code >= 400:
                return ActionResult(answer=_safe_error(resp), intent=intent, tool_name="get_leave_balance", status="ERROR")
            balances = resp.json()
            summary = ", ".join(f"{b['leave_type']}: {b['balance_days']} days" for b in balances) or "No balance records found."
            return ActionResult(answer=summary, intent=intent, tool_name="get_leave_balance", status="SUCCESS")

        if intent == "CREATE_TICKET":
            resp = await api_tools.create_ticket(payload, user.access_token)
            if resp.status_code >= 400:
                return ActionResult(answer=_safe_error(resp), intent=intent, tool_name="create_ticket", status="ERROR")
            data = resp.json()
            return ActionResult(
                answer=f"Ticket created: \"{payload['title']}\" (priority: {payload['priority']}).",
                intent=intent, tool_name="create_ticket", status="SUCCESS",
                records_accessed=[data.get("id")] if isinstance(data, dict) and data.get("id") else [],
            )

        if intent == "CREATE_ANNOUNCEMENT":
            resp = await api_tools.create_announcement(payload, user.access_token)
            if resp.status_code >= 400:
                return ActionResult(answer=_safe_error(resp), intent=intent, tool_name="create_announcement", status="ERROR")
            return ActionResult(answer=f"Announcement posted: \"{payload['title']}\".", intent=intent,
                                 tool_name="create_announcement", status="SUCCESS")

        if intent in ("APPROVE_LEAVE", "REJECT_LEAVE"):
            request_id = payload.get("leave_request_id")
            if not request_id:
                return ActionResult(
                    answer="I couldn't identify which leave request this refers to — please specify the employee and try again.",
                    intent=intent, status="ERROR",
                )
            new_status = "APPROVED" if intent == "APPROVE_LEAVE" else "REJECTED"
            resp = await api_tools.update_leave_request(request_id, {"status": new_status}, user.access_token)
            if resp.status_code >= 400:
                return ActionResult(
                    answer=_safe_error(resp), intent=intent, tool_name="update_leave_request", status="ERROR",
                )
            verb = "approved" if intent == "APPROVE_LEAVE" else "rejected"
            return ActionResult(
                answer=f"{payload.get('employee_name', 'The')}'s "
                       f"{payload.get('leave_type', '').lower()} leave request has been {verb}.",
                intent=intent, tool_name="update_leave_request", status="SUCCESS",
                records_accessed=[request_id],
            )

        if intent == "VIEW_PROJECTS":
            return ActionResult(answer="Use the SQL assistant tab to view your project assignments.", intent=intent)

        return ActionResult(answer="This action isn't wired up yet in this demo build.", intent=intent, status="ERROR")

    except Exception as exc:  # noqa: BLE001
        return ActionResult(answer=f"Something went wrong performing this action: {exc}", intent=intent, status="ERROR")


def _safe_error(resp) -> str:
    """Never pass raw backend error bodies straight through to chat."""
    if resp.status_code == 403:
        return "You do not have permission to perform this action."
    if resp.status_code == 404:
        return "I couldn't find the record this action refers to."
    if resp.status_code == 422:
        return "Some of the details for this action look invalid — could you clarify?"
    return "The action couldn't be completed right now."
