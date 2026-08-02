"""
Backend API tool wrappers for the HR Action Agent.

CRITICAL RULE: every function here calls an existing, already-
authorized HTTP endpoint using the *current user's own bearer token*.
None of these functions touch the database directly. This is what
keeps existing validation, RBAC, and business rules (leave balance
checks, approval permissions, etc.) as the single source of truth —
the agent can only do what the human could already do by clicking
through the app with their own login.

Connection handling: these calls loop back into the *same* running
server over HTTP (self-referential, by design — see module docstring
above). A single shared, lazily-created AsyncClient is reused across
every call rather than opening a fresh TCP connection per tool call.
Beyond the obvious overhead, repeatedly opening/closing many
short-lived loopback connections is a real problem on Windows: it
piles up sockets in TIME_WAIT, and Windows' slower ephemeral-port
recycling can eventually stall a *new* connection attempt — including
one that has nothing to do with the action agent — waiting for a free
port. Reusing one keep-alive connection avoids that churn entirely.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings

BASE_URL = get_settings().API_TOOLS_BASE_URL

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=10)
    return _client


async def aclose_client() -> None:
    """Called from the app's shutdown hook so the process doesn't leak
    the shared connection when the server itself stops."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


async def create_leave_request(payload: dict, access_token: str) -> httpx.Response:
    return await _get_client().post("/api/v1/leaves/requests", json=payload, headers=_headers(access_token))


async def update_leave_request(request_id: int, payload: dict, access_token: str) -> httpx.Response:
    return await _get_client().patch(f"/api/v1/leaves/requests/{request_id}", json=payload, headers=_headers(access_token))


async def get_leave_balance(access_token: str) -> httpx.Response:
    return await _get_client().get("/api/v1/leaves/balance", headers=_headers(access_token))


async def create_ticket(payload: dict, access_token: str) -> httpx.Response:
    return await _get_client().post("/api/v1/tickets", json=payload, headers=_headers(access_token))


async def update_ticket(ticket_id: int, payload: dict, access_token: str) -> httpx.Response:
    return await _get_client().patch(f"/api/v1/tickets/{ticket_id}", json=payload, headers=_headers(access_token))


async def create_announcement(payload: dict, access_token: str) -> httpx.Response:
    return await _get_client().post("/api/v1/announcements", json=payload, headers=_headers(access_token))


async def assign_employee_to_project(employee_id: int, payload: dict, access_token: str) -> httpx.Response:
    return await _get_client().post(f"/api/v1/employees/{employee_id}/projects", json=payload, headers=_headers(access_token))
