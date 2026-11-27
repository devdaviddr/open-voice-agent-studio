from fastapi.testclient import TestClient

from ovas_runtime import __version__
from ovas_runtime.main import app


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok", "version": __version__}
