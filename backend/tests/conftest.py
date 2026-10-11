"""Pre-scaffolded pytest fixtures for the FastAPI backend.

Tests hit the live uvicorn process managed by supervisor (not an in-process ASGI app), so
the app under test is the same one the frontend and Playwright see. Do NOT re-create this
file — add app-specific fixtures below the marker at the bottom.
"""

import os

import httpx
import pytest
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    """Absolute URL for an /api route: api_url("/status") -> http://localhost:8001/api/status."""
    return f"{API_URL}{path}"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture
def client():
    """Sync httpx client rooted at /api — the default for endpoint tests.

    Example:
        def test_status(client):
            assert client.get("/status").status_code == 200
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        username = os.environ.get("AUDITPRO_ADMIN_USERNAME", "auditpro-admin")
        password = os.environ.get("AUDITPRO_ADMIN_PASSWORD", "")
        if password:
            login = c.post("/auth/login", json={"username": username, "password": password})
            assert login.status_code == 200, f"Test auth setup failed: {login.status_code} {login.text}"
        yield c


@pytest_asyncio.fixture
async def aclient():
    """Authenticated async variant for tests that use protected API routes."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        username = os.environ.get("AUDITPRO_ADMIN_USERNAME", "auditpro-admin")
        password = os.environ.get("AUDITPRO_ADMIN_PASSWORD", "")
        if password:
            login = await c.post(
                "/auth/login", json={"username": username, "password": password}
            )
            assert login.status_code == 200, (
                f"Test auth setup failed: {login.status_code} {login.text}"
            )
        yield c


# --- app-specific fixtures below this line ---
