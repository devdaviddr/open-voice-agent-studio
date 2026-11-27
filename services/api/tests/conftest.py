import os
import subprocess
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Bring the test database (make test-db) to the latest migration once per run."""
    assert "test" in os.environ.get("OVAS_DATABASE_URL", ""), "run API tests via `make test`"
    subprocess.run(
        ["alembic", "-c", str(API_DIR / "alembic.ini"), "downgrade", "base"],
        check=True,
        cwd=API_DIR,
    )
    subprocess.run(
        ["alembic", "-c", str(API_DIR / "alembic.ini"), "upgrade", "head"], check=True, cwd=API_DIR
    )
