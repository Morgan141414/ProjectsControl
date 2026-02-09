import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    import app.core.config
    import app.db.session
    import app.main

    importlib.reload(app.core.config)
    importlib.reload(app.db.session)
    importlib.reload(app.main)

    with TestClient(app.main.app) as test_client:
        yield test_client
