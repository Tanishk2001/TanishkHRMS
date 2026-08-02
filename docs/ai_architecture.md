# AI Architecture — NovaWorks PeopleOps Copilot

## Overview

The AI layer sits between the existing Next.js frontend and the existing
FastAPI + SQLAlchemy HRMS backend. It never talks to the database directly
for writes — it either reads via a guardrailed, read-only SQL path, or it
calls the same authenticated backend API endpoints a human user would hit
by clicking through the app.

```
Next.js (ai-copilot page, chat panel)
        │  JWT bearer token
        ▼
FastAPI  /api/v1/chat/{policy,sql,actions,router}
        │
        ▼
get_current_user()  — decodes JWT, loads Employee, builds CurrentUser
        │
        ▼
services/ai/permissions.py  — single source of truth for AI RBAC
        │
   ┌────┴─────────────┬───────────────────┐
   ▼                   ▼                   ▼
policy_rag.py     sql_agent.py       action_agent.py
   │                   │                   │
   ▼                   ▼                   ▼
vector_store.py   sql_guardrails.py   api_tools.py (httpx)
   │                   │                   │
   ▼                   ▼                   ▼
hr_policies table  SELECT-only DB     existing endpoints:
(TF-IDF retrieval)  query execution    /leaves, /tickets,
                                       /announcements, /employees
                                            │
                                            ▼
                                     existing service-layer
                                     validation (balance checks,
                                     date checks, RBAC) — DB writes
                                     happen ONLY here
        │
        ▼
services/ai/audit.py → ai_audit_logs table
```

## Components

### 1. Policy RAG Assistant (`services/ai/policy_rag.py`, `vector_store.py`, `embeddings.py`)

- **Chunking**: `hr_policies.content` is split on paragraph boundaries,
  with long paragraphs hard-wrapped (700 chars, 100 char overlap) so
  retrieval doesn't lose context at edges.
- **Embeddings**: TF-IDF (scikit-learn), not a downloaded neural model.
  This was a deliberate choice — it keeps the whole system runnable fully
  offline with no model-hub access required, while still giving useful
  similarity ranking over short, vocabulary-distinct HR policy text. The
  `TfidfEmbedder` class is an isolated swap-out point; replacing it with a
  hosted embeddings API only requires matching its `fit` / `embed_query` /
  `top_k` interface.
- **Retrieval**: cosine similarity, top-k (default 3), with a minimum
  similarity floor (`POLICY_MIN_SIMILARITY`) below which the system
  returns an explicit "insufficient context" refusal rather than guessing.
- **Generation**: if `ANTHROPIC_API_KEY` is configured, an LLM call
  generates the answer using *only* the retrieved chunks, which are
  wrapped in `<policy_chunk>` tags and explicitly labeled as untrusted
  reference data, not instructions. If no key is configured (or the call
  fails), a deterministic extractive fallback selects the most
  keyword-relevant sentences from the retrieved chunks — the system is
  fully functional and testable without any LLM credentials.
- **Prompt-injection defense**: chunk text is scanned for
  instruction-like patterns ("ignore previous instructions", "reveal
  all salaries", etc.) and flagged inline in the prompt; the system
  prompt explicitly tells the model never to follow directives found in
  retrieved content. The extractive fallback path has no code execution
  surface at all — it only copies substrings.

### 2. SQL Agent (`services/ai/sql_agent.py`, `sql_guardrails.py`)

- **Default path (EMPLOYEE / MANAGER)**: natural-language intent is
  matched with regex against a small library of *parameterized SQL
  templates*. The model (if any) never produces free-text SQL for these
  roles — only template parameters (e.g. a skill name) are extracted.
  This makes the common-case path safe by construction, independent of
  the guardrail layer.
- **Admin-only free-form path**: if intent doesn't match a template and
  the user is an ADMIN, and an LLM key is configured, the agent asks the
  model for a single read-only SELECT statement against a documented
  schema. This path is a convenience, not a bypass — it is validated by
  the exact same guardrail function as the template path.
- **Guardrail layer (`sql_guardrails.validate_sql`)** — the single choke
  point every generated query passes through before execution:
  - Parses with `sqlparse`, rejects anything that isn't exactly one
    `SELECT` statement.
  - Rejects `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/REPLACE/TRUNCATE/
    PRAGMA/ATTACH/DETACH/GRANT/REVOKE/VACUUM/EXEC/EXECUTE/CALL` by
    word-boundary regex.
  - Rejects `--` / `/* */` comments (a common technique for hiding a
    follow-on statement or disabling a WHERE clause).
  - Rejects references to any table outside an explicit allow-list.
  - Rejects references to a hard-coded list of sensitive columns
    (`hashed_password`, `bank_*`, `pan_*`, `date_of_birth`,
    `current_salary_usd`, `profile_photo_*`).
  - Injects/normalizes a `LIMIT` clause to `SQL_AGENT_MAX_ROWS` (200).
  - This is unit-tested directly in `test_sql_guardrails.py`
    independent of any LLM availability — see `docs/ai_eval_results.md`.
- **Row-level scoping**: `permissions.scope_for_sql()` returns SELF /
  TEAM / ALL based on role; templates bind `:employee_id` /
  `:manager_id` as query parameters (never string-concatenated).
- Raw SQL is only ever returned to the caller if
  `permissions.can_view_raw_sql(user)` allows it for that role.

### 3. HR Task Automation Agent (`services/ai/action_agent.py`, `api_tools.py`)

- **Intent extraction**: regex-based classification (`classify_intent`)
  plus per-intent structured field extraction (dates via
  `python-dateutil`, leave type, ticket priority, reason/title text).
- **Permission gate runs before extraction of the final payload** for
  privileged intents (approve/reject leave, update ticket, create
  announcement, assign to project) — an unauthorized user gets a
  generic "You do not have permission..." response and the agent stops;
  it never even attempts to build or send the request.
- **Human-in-the-loop confirmation**: high-impact intents
  (`HIGH_IMPACT_INTENTS`) return `NEEDS_CONFIRMATION` with the
  extracted payload echoed back as `pending_action`. The frontend
  re-sends the same payload with `confirm=true` to proceed. This is
  stateless — no server-side session/cache is needed.
- **Approve/reject leave name resolution**: "Approve Priya Dev's leave
  request" is resolved to a specific `PENDING` `leave_request_id` via
  `_resolve_pending_leave_request()` — a read-only, role-scoped lookup
  (a manager only sees their own team's requests; an admin sees all).
  Zero matches or more than one match both return a clear message
  instead of guessing; this resolution happens server-side, before the
  confirmation prompt is shown, so the confirmation itself names the
  specific leave dates being approved/rejected.
- **Tool calling, not DB writes**: every mutation goes through
  `api_tools.py`, which makes real HTTP calls to the existing
  `/api/v1/leaves`, `/api/v1/tickets`, `/api/v1/announcements`, and
  `/api/v1/employees/{id}/projects` endpoints using **the current
  user's own JWT**. Those endpoints contain the actual business rules
  (leave balance checks, date validation, RBAC) — the agent cannot do
  anything a human couldn't already do through the existing UI.
- **Safe error handling**: `_safe_error()` maps raw HTTP status codes
  from the backend (403/404/422) to generic, non-leaking messages
  instead of forwarding raw exception text to the chat.

### 4. AI Router (`/api/v1/chat/router`)

A lightweight, rule-based (non-LLM) keyword classifier that returns
`{intent, confidence, reason}`. It is read-only and doesn't execute
anything — useful for a unified chat entrypoint if the frontend wants
one input box instead of three tabs.

### 5. RBAC (`services/ai/permissions.py`)

Every capability check used by every agent lives in one file, matching
the AI Permissions Matrix in `docs/ai_permissions_matrix.md`. Refusals
are worded generically and never confirm or deny that a specific
record exists (see `PermissionDenied` docstring).

### 6. Audit Logging (`services/ai/audit.py`, `models/ai_audit_log.py`)

Every one of the three chat endpoints calls `write_audit_log()` exactly
once per request, capturing user id, role, message (truncated),
detected intent, tool/API called, status
(`SUCCESS`/`DENIED`/`ERROR`/`NO_ANSWER`/`NEEDS_CONFIRMATION`), and
wall-clock `latency_ms`. No secrets, tokens, passwords, or bank/PAN
numbers are ever written to this table.

Two read endpoints expose this data back to the frontend:

- `GET /api/v1/chat/audit/recent?limit=N` — self-scoped to the caller
  (any role); powers the "Recent AI Actions" panel.
- `GET /api/v1/chat/audit/usage` — company-wide aggregates (total
  requests, requests by intent/tool, failed-permission-attempt count,
  average latency, RAG no-answer rate, SQL-blocked-query count),
  gated by `permissions.can_view_ai_usage_dashboard` (admin-only);
  powers the AI Usage Dashboard (bonus #8, `/ai-copilot/usage`).

## Model / provider used

- **LLM**: Anthropic Claude (`claude-sonnet-4-6` by default,
  configurable via `LLM_MODEL`), used only for (a) grounded policy
  answer generation and (b) admin-only free-form SQL generation. Both
  call sites are optional — the app has no hard dependency on an LLM
  being configured, by design, so it can be graded/run offline.
- **Embeddings**: scikit-learn TF-IDF, fully local, no external calls.

## Setup instructions

```bash
cd backend
pip install -r requirements.txt --break-system-packages
export ANTHROPIC_API_KEY=sk-ant-...   # optional — omit to run fully offline
alembic upgrade head                  # applies migrations (see alembic/versions/)
python -m app.seed_data               # clears + reseeds rows (safe to re-run)
python -m uvicorn app.main:app --reload --port 8000

cd ../frontend
cp .env.example .env.local
npm install
npm run dev   # http://localhost:3000
```

Seed accounts (see `app/seed_data.py`):

| Role     | Email                          | Password     |
|----------|---------------------------------|--------------|
| Admin    | admin@novaworks.com            | admin123     |
| Manager  | rahul.manager@novaworks.com    | manager123   |
| Employee | employee@novaworks.com         | employee123  |

## Database schema management

Schema is owned entirely by Alembic migrations under
`backend/alembic/versions/`, not by SQLAlchemy's `create_all()` — the
app no longer calls `create_all()` on startup at all. This matters for
the same reason it would in the real NovaWorks environment: you can't
safely re-create a production table that already has employee data in
it, but you can apply an incremental, reversible migration to it.

- `0001_initial_hrms_schema.py` — the pre-existing CB Nest tables
  (employees, departments, projects, skills, leaves, tickets,
  announcements, hr_policies)
- `0002_add_ai_audit_logs.py` — adds the `ai_audit_logs` table
  introduced by this AI layer; `down_revision` chains it after 0001,
  and its `downgrade()` cleanly drops just that one table

Run `alembic upgrade head` once before first starting the app (and
after pulling any future migration). `python -m app.seed_data` only
clears and reinserts rows — it never touches schema — so it's safe to
re-run at any time against an already-migrated database.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret — **must** be overridden in any real deployment |
| `DATABASE_URL` | `sqlite:///./cb_nest.db` | SQLAlchemy connection string |
| `ANTHROPIC_API_KEY` | unset | Enables LLM-backed policy generation + admin free-form SQL; app runs fully without it |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model name for the LLM client |
| `SQL_AGENT_MAX_ROWS` | `200` | Hard row cap enforced by the guardrail layer |
| `POLICY_TOP_K` | `3` | Number of policy chunks retrieved per question |
| `POLICY_MIN_SIMILARITY` | `0.12` | Similarity floor below which the RAG assistant refuses to answer |

## Known limitations

- The SQL Agent's template library was broadened (12 templates covering
  projects by status, department headcount, pending team leave requests,
  full directory listing, named-manager reporting lines, and more
  flexible skill/assignment phrasing) but is still a fixed set, not
  free-form generation, for EMPLOYEE/MANAGER roles. A genuinely novel
  ad-hoc question from a non-admin still falls back to a "couldn't match
  that" message rather than attempting unsafe free-form generation —
  this remains an intentional safety trade-off, not an oversight.
- TF-IDF retrieval is lexical, not semantic — it won't match a policy
  question that shares no vocabulary with the policy text. Swapping in
  a hosted embeddings model is a one-file change (`embeddings.py`).
- No streaming responses, no LangGraph orchestration, no tracing —
  these were left as the bonus items they're listed as in the
  assignment, in favor of getting the required core paths fully
  working and tested first.
- The AI usage dashboard (bonus #8) and the "Recent AI Actions" panel
  are now implemented (`GET /api/v1/chat/audit/usage`, admin-only;
  `GET /api/v1/chat/audit/recent`, self-scoped for any role) — see
  `frontend/app/ai-copilot/usage/page.tsx` and
  `frontend/components/ai/recent-actions-panel.tsx`.
- Prompt injection defense (bonus #6) now has dedicated coverage in
  `tests/test_prompt_injection.py`, including an actual malicious
  instruction embedded inside a seeded policy DOCUMENT (not just the
  user's question) — see `seed_policy_06.md` in `seed_data.py`. The
  action agent has no LLM in its intent-extraction path at all, so it
  is not susceptible to prompt injection by construction; the SQL
  agent's structural defense (every generated query passes through
  `validate_sql()` before execution, regardless of what produced it)
  matters more here than any system-prompt wording.

## Automated test suite

`backend/tests/` is a self-contained pytest suite (43 tests) wired into
CI via `.github/workflows/backend-tests.yml` — it runs on every push/PR
that touches the backend, requires no manually-started server and no
API keys, and covers Policy RAG, the SQL agent (including the RBAC-gated
`pending_team_leave_requests` template and the salary/DROP-TABLE
security cases), the action agent (confirmation flow, multiple
approve/reject name-matching phrasings, permission denials), and the
SQL guardrails as pure unit tests. `backend/conftest.py` boots a real
uvicorn subprocess against a disposable temp SQLite DB on a random free
port per test session — this matters because the action agent's tool
calls are genuine HTTP requests to the running app (see "Tool calling,
not DB writes" above), so an in-process ASGI transport wouldn't
exercise that path faithfully. See `.github/workflows/frontend-build.yml`
for the companion frontend build check.

## Security decisions

- **No AI-initiated raw SQL writes anywhere in the codebase** — the SQL
  agent's execution path only ever calls `db.execute(text(sql), params)`
  after `validate_sql()` has confirmed a single SELECT with no forbidden
  keywords/tables/columns; the action agent never imports SQLAlchemy
  models at all — it only speaks HTTP to existing endpoints.
- **Authorization enforced server-side, twice**: once in
  `services/ai/permissions.py` before the AI layer acts, and again
  inside the underlying `/api/v1/*` endpoints themselves (e.g.
  `leaves.py` re-checks `user.role in ("MANAGER", "ADMIN")` on
  approve/reject independent of what the AI layer already checked).
  Frontend has no authorization logic at all.
- **Refusals don't leak existence** — permission denials use a fixed
  generic message rather than "found X but can't show it."
