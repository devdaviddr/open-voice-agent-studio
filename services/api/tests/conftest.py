import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

from ovas_api.db import get_engine
from ovas_api.main import app

API_DIR = Path(__file__).resolve().parents[1]
ORIGIN = "http://localhost:5173"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Bring the test database (make test-db) down and up again once per run."""
    assert "test" in os.environ.get("OVAS_DATABASE_URL", ""), "run API tests via `make test`"
    ini = str(API_DIR / "alembic.ini")
    subprocess.run(["alembic", "-c", ini, "downgrade", "base"], check=True, cwd=API_DIR)
    subprocess.run(["alembic", "-c", ini, "upgrade", "head"], check=True, cwd=API_DIR)


@pytest.fixture(autouse=True)
async def clean_tables(migrated_database):
    async with get_engine().begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename <> 'alembic_version'"
                )
            )
        ).scalars()
        names = ", ".join(tables)
        if names:
            await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"origin": ORIGIN},
    )


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with make_client() as c:
        yield c


async def signup(c: httpx.AsyncClient, email: str, password: str = "correct horse battery") -> dict:
    res = await c.post("/v1/auth/signup", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture(name="make_client")
def make_client_fixture():
    return make_client


@pytest.fixture(name="signup")
def signup_fixture():
    return signup


@pytest.fixture
async def owner(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """A client signed in as the workspace owner."""
    await signup(client, "owner@example.com")
    return client
