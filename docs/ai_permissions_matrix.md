# AI Permissions Matrix

This mirrors the RBAC enforced in `backend/app/services/ai/permissions.py`.
Every function listed under "Enforced by" is the actual code path — this
table is documentation of that code, not a separate spec that could drift
from it.

| AI Capability | Employee | Manager | Admin | Enforced by |
|---|---|---|---|---|
| Ask HR policy questions | ✅ | ✅ | ✅ | No restriction — `policy_rag` is role-agnostic |
| Ask own leave balance | ✅ | ✅ | ✅ | `can_view_own_leave_balance` |
| Ask another employee's leave balance | ❌ | Team only | ✅ | `can_view_other_leave_balance` |
| View own project assignments | ✅ | ✅ | ✅ | `_tmpl_my_project_assignments` (scoped to `employee_id = user.id`) |
| View all project assignments | ❌ | Limited | ✅ | `can_view_all_project_assignments`, `scope_for_sql` |
| Search employees by skill | Limited | ✅ | ✅ | `can_search_employees_by_skill`; row cap via `SQL_AGENT_MAX_ROWS` |
| Generate free-form SQL over HR data | ❌ (template-only) | ❌ (template-only) | ✅ | `can_generate_free_form_sql` |
| View raw SQL in response | ❌ | Optional | Optional | `can_view_raw_sql` |
| Create own leave request | ✅ | ✅ | ✅ | `action_agent.APPLY_LEAVE` → `POST /api/v1/leaves/requests` |
| Approve/reject leave | ❌ | ✅ | ✅ | `can_approve_or_reject_leave`, re-checked in `leaves.py` endpoint |
| Create ticket | ✅ | ✅ | ✅ | `action_agent.CREATE_TICKET` |
| Assign/update ticket | ❌ | ✅ | ✅ | `can_assign_or_update_ticket`, re-checked in `tickets.py` endpoint |
| Create announcement | ❌ | ✅ | ✅ | `can_create_announcement`, re-checked in `announcements.py` endpoint |
| Assign employee to project | ❌ | ✅ | ✅ | `can_assign_employee_to_project`, re-checked in `employees.py` endpoint |
| Access payroll data | ❌ | ❌ | ✅ (own systems only, not via this AI layer's SQL agent) | `can_access_payroll`; `current_salary_usd` is also globally blocked by `sql_guardrails.FORBIDDEN_COLUMNS` regardless of role |
| Access bank/PAN/password fields | ❌ | ❌ | ❌ | `can_access_bank_or_pan_or_password` returns `False` unconditionally; also hard-blocked at the SQL guardrail layer for every role including admin |

## Refusal wording

Every denial in the AI layer uses a fixed, generic message:

> "You do not have permission to perform this action."
> "You do not have permission to view another employee's payroll information."

The system never says "I found X but can't show it" — that would leak
the existence of the record to a user who isn't authorized to know
about it in the first place. See `permissions.PermissionDenied` and
`action_agent._safe_error`.

## Two-layer enforcement

AI-layer checks (`services/ai/permissions.py`) are a first gate that
lets the agent fail fast and cheaply, without ever building/sending a
request. The underlying HRMS API endpoints re-check authorization
independently (e.g. `leaves.py::update_leave_request_status` checks
`user.role not in ("MANAGER", "ADMIN")` itself). This means a bug in
the AI layer's permission check can't turn into a real authorization
bypass — the service layer is still the actual source of truth, per
the assignment's architecture rule.
