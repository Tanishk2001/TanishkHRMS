from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (ensures all models are registered, e.g. for tooling/reflection)
from app.core.config import get_settings
from app.api.v1.endpoints import auth, leaves, tickets, announcements, employees, policies, attendance, reports, assets, exits, engagement, time_entries, chat
from app.services.ai import api_tools

settings = get_settings()

app = FastAPI(title="CB Nest — PeopleOps Copilot")

# allow_origins takes the deployed frontend's exact URL (set via the
# FRONTEND_ORIGIN env var in production); allow_origin_regex separately
# covers http://localhost:<any port> for local dev. Both can be active
# at once — this doesn't require choosing one or the other.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN else [],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema is managed by Alembic migrations (see alembic/versions/), not
# by create_all() — run `alembic upgrade head` before starting the app.
# This matches how a real, already-populated production database must
# be evolved: incrementally and reversibly, never by dropping/recreating.

app.include_router(auth.router)
app.include_router(leaves.router)
app.include_router(tickets.router)
app.include_router(announcements.router)
app.include_router(employees.router)
app.include_router(policies.router)
app.include_router(attendance.router)
app.include_router(reports.router)
app.include_router(assets.router)
app.include_router(exits.router)
app.include_router(engagement.router)
app.include_router(time_entries.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("shutdown")
async def _close_shared_action_agent_client():
    await api_tools.aclose_client()
