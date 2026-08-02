"""
Central RBAC matrix for AI features.

Every AI code path (RAG, SQL agent, action agent) must consult this
module rather than inventing its own ad-hoc checks. This keeps the
"AI Permissions Matrix" in one auditable place and mirrors the
permissions already enforced by the existing HRMS backend APIs.

Design rule: refusals must never leak whether a record exists ("You
do not have permission to view X" — not "I found X but can't show it").
"""
from dataclasses import dataclass
from enum import Enum

from app.core.security import CurrentUser


class Role(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class PermissionDenied(Exception):
    """Raised for any AI-layer authorization failure. Message must be
    generic and must never confirm/deny the existence of a record."""

    def __init__(self, message: str = "You do not have permission to perform this action."):
        self.message = message
        super().__init__(message)


# --- Capability checks -----------------------------------------------------

def can_view_own_leave_balance(user: CurrentUser) -> bool:
    return True  # all roles


def can_view_team_attendance(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_view_ai_usage_dashboard(user: CurrentUser) -> bool:
    # Company-wide AI usage metrics (request volume, denied-permission
    # count, etc.) are an admin-only surface for the same reason
    # cross-department analytics is — a manager's AI activity is
    # already visible to them via their own "Recent AI Actions" panel.
    return user.role == Role.ADMIN


def can_view_analytics(user: CurrentUser) -> bool:
    # Company-wide reports are an HR/admin surface, not a manager one —
    # a manager already has team-scoped views (attendance, pending
    # leaves) elsewhere; cross-department analytics stays admin-only.
    return user.role == Role.ADMIN


def can_decide_exit_request(user: CurrentUser, target_manager_id: int | None) -> bool:
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.MANAGER:
        return target_manager_id == user.id
    return False


def can_manage_exit_checklist_and_completion(user: CurrentUser) -> bool:
    # Deactivating an employee is irreversible-in-practice and touches
    # payroll/access-adjacent territory, so this stays admin-only even
    # though a manager can approve the resignation itself.
    return user.role == Role.ADMIN


def can_manage_polls(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_view_team_time_entries(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_view_other_leave_balance(user: CurrentUser, target_employee_id: int, target_manager_id: int | None) -> bool:
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.MANAGER:
        return target_manager_id == user.id
    return False


def can_view_all_project_assignments(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)  # manager limited to team, enforced at query time


def can_search_employees_by_skill(user: CurrentUser) -> bool:
    return True  # employees get limited (self + public directory), enforced at query level


def can_generate_free_form_sql(user: CurrentUser) -> bool:
    # Employees and managers are restricted to a safe template library;
    # only admins may trigger broader ad-hoc SQL generation.
    return user.role == Role.ADMIN


def can_view_raw_sql(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_approve_or_reject_leave(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_assign_or_update_ticket(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_create_announcement(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_assign_employee_to_project(user: CurrentUser) -> bool:
    return user.role in (Role.ADMIN, Role.MANAGER)


def can_access_payroll(user: CurrentUser, target_employee_id: int) -> bool:
    if user.role == Role.ADMIN:
        return True
    return False  # employees/managers: blocked entirely from the AI layer


def can_access_bank_or_pan_or_password(user: CurrentUser) -> bool:
    return False  # nobody, ever, via AI


@dataclass
class ScopeFilter:
    """Describes how a query result set must be scoped for this user.
    Consumed by the SQL agent to add WHERE clauses / template params."""
    scope: str  # "SELF" | "TEAM" | "ALL"
    employee_id: int
    manager_id: int | None
    department_id: int | None


def scope_for_sql(user: CurrentUser) -> ScopeFilter:
    if user.role == Role.ADMIN:
        return ScopeFilter(scope="ALL", employee_id=user.id, manager_id=user.manager_id,
                            department_id=user.department_id)
    if user.role == Role.MANAGER:
        return ScopeFilter(scope="TEAM", employee_id=user.id, manager_id=user.manager_id,
                            department_id=user.department_id)
    return ScopeFilter(scope="SELF", employee_id=user.id, manager_id=user.manager_id,
                        department_id=user.department_id)
