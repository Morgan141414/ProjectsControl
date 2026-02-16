import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    # Ensure fresh app module graph per test run, so env overrides
    # (especially DATABASE_URL) are respected by all imported routes/deps.
    to_drop = [
        name
        for name in list(sys.modules)
        if name == "app.main"
        or name == "app.core.config"
        or name == "app.core.deps"
        or name == "app.db.session"
        or name.startswith("app.api.routes")
    ]
    for name in to_drop:
        sys.modules.pop(name, None)

    import app.core.config
    import app.db.session
    import app.core.deps
    import app.main

    importlib.reload(app.core.config)
    importlib.reload(app.db.session)
    importlib.reload(app.core.deps)
    importlib.reload(app.main)

    with TestClient(app.main.app) as test_client:
        yield test_client
