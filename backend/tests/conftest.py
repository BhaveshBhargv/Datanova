"""Pytest fixtures: isolated SQLite DB, temp file storage, and a test client."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.storage import storage
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Redirect dataset artifacts (Parquet/originals) into the test's temp dir.
    monkeypatch.setattr(storage, "base", Path(tmp_path).resolve())

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth_headers(client):
    """Factory: register + log in a user, return its Authorization header."""

    def _make(email: str = "alice@example.com", password: str = "supersecret123"):
        client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Tester"},
        )
        r = client.post(
            "/api/auth/login", data={"username": email, "password": password}
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make
