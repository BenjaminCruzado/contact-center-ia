from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helpers import make_auth_header

client = TestClient(app)


def test_login_returns_token_and_role() -> None:
    response = client.post(
        "/auth/login",
        json={"username": "usuario", "password": "user123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["role"] == "user"
    assert payload["access_token"]


def test_auth_me_returns_current_user() -> None:
    response = client.get("/auth/me", headers=make_auth_header("admin"))

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_login_rejects_invalid_credentials() -> None:
    response = client.post(
        "/auth/login",
        json={"username": "usuario", "password": "incorrecta"},
    )

    assert response.status_code == 401
