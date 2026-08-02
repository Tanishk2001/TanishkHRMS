# CB Nest — NovaWorks PeopleOps Copilot

AI-powered HR operations copilot built on top of a full-stack CB Nest
HRMS: a Policy RAG assistant, a read-only SQL agent, and an HR task
automation agent that performs actions through the existing backend
APIs — never through direct database writes.

See `docs/ai_architecture.md` for the full design writeup,
`docs/ai_permissions_matrix.md` for the RBAC matrix, and
`docs/ai_eval_results.md` for actual test results from a live run.

## Quick start

### Backend

```bash
cd backend
pip install -r requirements.txt --break-system-packages
export ANTHROPIC_API_KEY=sk-ant-...   # optional — app runs fully without it
alembic upgrade head                  # applies migrations (backend/alembic/versions/)
python -m app.seed_data               # clears + reseeds rows (safe to re-run)
python -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive API docs.

Seed accounts:

| Role     | Email                        | Password    |
|----------|-------------------------------|-------------|
| Admin    | admin@novaworks.com          | admin123    |
| Manager  | rahul.manager@novaworks.com  | manager123  |
| Employee | employee@novaworks.com       | employee123 |

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000, sign in with one of the seed accounts above,
and you'll land on `/ai-copilot` with three tabs: **Ask HR Policy**,
**Ask About People & Projects**, and **Automate HR Task**.

### Verifying it all works

**Automated suite (recommended)** — self-contained, boots its own throwaway
server + database, no manual setup needed, and runs automatically in CI on
every push (see `.github/workflows/backend-tests.yml`):

```bash
cd backend
pip install -r requirements.txt   # includes pytest
python -m pytest -v
```

Covers Policy RAG (including injection embedded in an actual policy
document, not just the user's question — see `test_prompt_injection.py`),
the SQL agent (RBAC-gated and security cases), the HR action agent
(confirmation flow, multiple approve/reject phrasings, permission
denials), the router, the SQL guardrails, and the AI usage dashboard /
recent-actions endpoints, as pure unit + integration tests. Nothing here
requires an already-running server, a seeded database, or an LLM API
key — each test session spins up its own on a random free port and
tears it down afterward.

**Manual scripts** — handy for a quick sanity check against a server
you already have running (e.g. while developing):

```bash
cd backend
python smoke_test.py            # exercises all 3 chat endpoints + RBAC + confirmation flow
python test_sql_guardrails.py   # unit-tests the SQL safety layer directly
```

Both scripts require the backend server to already be running (see
above) and print pass/fail results for every case inline.

## Project layout

```
.github/workflows/       ← CI: backend pytest suite + frontend build, on every push
backend/
  alembic.ini, alembic/env.py, alembic/versions/                       ← schema migrations
    0001_initial_hrms_schema.py, 0002_add_ai_audit_logs.py
  app/
    core/          config, JWT auth
    db/            SQLAlchemy engine/session
    models/        HRMS domain models + AI audit log
    schemas/       Pydantic request/response models
    api/v1/endpoints/
      auth.py, leaves.py, tickets.py, announcements.py, employees.py, policies.py, attendance.py, reports.py, assets.py, exits.py, engagement.py, time_entries.py  ← existing HRMS APIs
      chat.py                                                          ← AI endpoints
    services/ai/
      policy_rag.py, embeddings.py, vector_store.py                    ← RAG
      sql_agent.py, sql_guardrails.py                                  ← SQL agent + safety
      action_agent.py, api_tools.py, permissions.py                    ← task automation + RBAC
      audit.py                                                         ← audit logging
    seed_data.py    (clears + reinserts rows — schema is migration-owned)
  tests/            ← automated pytest suite (self-contained, CI-wired)
  smoke_test.py, test_sql_guardrails.py, eval_dataset.json  ← manual/live-server scripts
frontend/
  app/dashboard/page.tsx    home page — the "Ask the Copilot" hero + live-data cards
  app/ai-copilot/page.tsx   the 3-tab chat interface
  app/{employees,attendance,leaves,time-tracking,assets,exits,engagement,announcements,policies,tickets,reports}/page.tsx
  components/layout/        sidebar, topbar, shell, dash-card
  components/ai/            chat panel, source list, SQL table, action card
  lib/api.ts                typed API client
docs/
  ai_architecture.md, ai_permissions_matrix.md, ai_eval_results.md
```

## Modules & roadmap

Beyond the four required AI capabilities, this project also implements a
growing slice of standard HRMS functionality: Core HR (employees,
departments, projects, skills), Leave Management, a Help Desk (tickets),
HR policy reference, **Attendance Management**, **Reports & Analytics**
(admin-only dashboards with real charts), **Asset Management**
(inventory, issue/return workflow), **Exit Management** (resignation →
approval → offboarding checklist → completion, which genuinely
deactivates the employee only once every checklist item — including a
live-verified asset return — is actually true), **Employee Engagement**
(Polls with live results and one-vote-per-person enforcement, plus
peer-to-peer Kudos), and **Time Tracking** (employees log hours only
against projects they're genuinely assigned to — validated against the
real assignment data, not just any project id — with a daily-hours
sanity cap and a manager/admin team view), alongside the original
Announcements module.

Measured against a full Zoho People/BambooHR-style feature set (ATS,
onboarding, payroll, performance management, LMS, time tracking, expense
management, asset management, document management, exit management,
compliance, and a visual workflow builder), those remain out of scope —
each is realistically its own multi-week build, not a quick addition,
and this project prioritizes depth (real business rules, RBAC, and a
tested automated suite for every module) over shallow breadth.

## Security notes

- AI agents never write to the database directly — all mutations go
  through the existing, already-validated backend API endpoints using
  the current user's own JWT.
- All generated SQL (template or LLM-produced) passes through a single
  guardrail function before execution: single-statement, SELECT-only,
  no forbidden keywords, no sensitive columns, hard row limit.
- Every AI interaction is audit-logged (user, role, intent, tool,
  status) without ever storing secrets, tokens, or sensitive PII.
- High-impact actions (approve/reject leave, create announcement,
  assign to project, update ticket) require explicit confirmation
  before the API call is made.

See `docs/ai_architecture.md` → "Known limitations" for what's
intentionally left out of this build (LangGraph orchestration,
streaming, tracing — listed as bonuses in the assignment).
