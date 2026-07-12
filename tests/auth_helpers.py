from app.services.auth_service import AuthService, AuthUser


def make_auth_header(role: str = "user") -> dict[str, str]:
    username = "usuario" if role == "user" else "admin"
    token, _ = AuthService().create_access_token(AuthUser(username=username, role=role))
    return {"Authorization": f"Bearer {token}"}
