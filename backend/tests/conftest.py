"""
Session-scoped fixtures for the automated test suite.

The action agent's tool calls (services/ai/api_tools.py) make *real*
HTTP requests to the running app — that's the whole point of the
"agent calls existing APIs, never raw SQL" architecture. So these
tests boot an actual uvicorn subprocess against a disposable, freshly
migrated + seeded SQLite database, rather than mocking anything out.
This is the same thing smoke_test.py does manually against a
developer's already-running server, just self-contained and
CI-friendly: no server needs to be started by hand first.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.remove(db_path)  # SQLAlchemy/Alembic create it fresh on first connect

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["API_TOOLS_BASE_URL"] = base_url
    env["JWT_SECRET"] = "test-secret-not-for-production"
    # Force-disable the LLM path for the test subprocess. Note this is
    # NOT the same as env.pop("ANTHROPIC_API_KEY", None): Settings also
    # reads a local .env file (SettingsConfigDict(env_file=".env")), and
    # an *absent* OS env var falls through to that .env value — so
    # popping the var doesn't actually stop a real key from a developer's
    # own .env file leaking into the test run. Setting it to "" does
    # take precedence over .env, and "" is falsy in LLMClient's
    # `if settings.ANTHROPIC_API_KEY:` check, so is_available stays False.
    env["ANTHROPIC_API_KEY"] = ""

    # Windows-specific: numpy/scikit-learn's underlying BLAS library can
    # spin up its own internal OS thread pool for math ops. When that
    # gets invoked from multiple FastAPI worker threads across several
    # requests (as the TF-IDF-based policy/SQL agents do), it can
    # deadlock silently on Windows — a single isolated request works
    # fine, but the server hangs permanently after a handful of calls
    # stack up. Forcing every math backend to single-threaded removes
    # the internal thread pool entirely, eliminating the deadlock. This
    # costs nothing here since the TF-IDF corpus is tiny (a handful of
    # short HR policy documents) — there's no real parallelism to lose.
    for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[_var] = "1"

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, env=env, check=True, capture_output=True, text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "app.seed_data"],
        cwd=BACKEND_DIR, env=env, check=True, capture_output=True, text=True,
    )

    log_fd, log_path = tempfile.mkstemp(suffix=".log")
    os.close(log_fd)
    log_file = open(log_path, "w")

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR, env=env,
        # A pipe here (the previous approach) is a classic deadlock trap:
        # nothing actively reads from subprocess.PIPE while the fixture
        # is just polling /health, so once uvicorn's per-request access
        # log fills the OS pipe buffer (small — ~64KB on Windows), the
        # child process blocks on its next stdout write and the whole
        # server freezes silently, mid-test-run, for no reason connected
        # to any specific request. Redirecting straight to a file needs
        # no reader and can never back up like this.
        stdout=log_file, stderr=subprocess.STDOUT,
    )

    try:
        healthy = False
        for _ in range(60):
            try:
                if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                    healthy = True
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.5)

        if not healthy:
            proc.terminate()
            log_file.flush()
            with open(log_path) as f:
                out = f.read()
            raise RuntimeError(f"Test server never became healthy.\n--- server output ---\n{out}")

        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(log_path):
            os.remove(log_path)


@pytest.fixture(scope="session")
def tokens(live_server):
    """Logs in all three seed roles once per session."""

    def login(email: str, password: str) -> str:
        r = httpx.post(f"{live_server}/api/v1/auth/login", json={"email": email, "password": password}, timeout=10)
        r.raise_for_status()
        return r.json()["access_token"]

    return {
        "admin": login("admin@novaworks.com", "admin123"),
        "manager": login("rahul.manager@novaworks.com", "manager123"),
        "employee": login("employee@novaworks.com", "employee123"),
    }


@pytest.fixture
def client(live_server):
    with httpx.Client(base_url=live_server, timeout=10) as c:
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
