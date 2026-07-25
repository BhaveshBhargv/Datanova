"""End-to-end tests for the Phase 1 auth flow."""

REGISTER = "/api/auth/register"
LOGIN = "/api/auth/login"
REFRESH = "/api/auth/refresh"
ME = "/api/users/me"

USER = {"email": "alice@example.com", "password": "supersecret123", "full_name": "Alice"}


def _register(client, **overrides):
    return client.post(REGISTER, json={**USER, **overrides})


def _login(client, email=USER["email"], password=USER["password"]):
    # OAuth2 password flow expects form-encoded `username`/`password`.
    return client.post(LOGIN, data={"username": email, "password": password})


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_creates_user(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == USER["email"]
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_email_conflicts(client):
    _register(client)
    r = _register(client)
    assert r.status_code == 409


def test_register_rejects_short_password(client):
    r = _register(client, password="short")
    assert r.status_code == 422


def test_login_returns_tokens(client):
    _register(client)
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(client):
    _register(client)
    r = _login(client, password="wrongpassword")
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    r = client.get(ME)
    assert r.status_code == 401


def test_protected_route_with_token(client):
    _register(client)
    token = _login(client).json()["access_token"]
    r = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == USER["email"]


def test_refresh_issues_new_access_token(client):
    _register(client)
    refresh_token = _login(client).json()["refresh_token"]
    r = client.post(REFRESH, json={"refresh_token": refresh_token})
    assert r.status_code == 200
    new_access = r.json()["access_token"]
    me = client.get(ME, headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_refresh_rejects_access_token_as_refresh(client):
    _register(client)
    access_token = _login(client).json()["access_token"]
    # An access token must not be usable at the refresh endpoint.
    r = client.post(REFRESH, json={"refresh_token": access_token})
    assert r.status_code == 401
