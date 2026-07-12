from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.config.settings import Settings, settings


class AuthError(Exception):
    """Error base de autenticación."""


class InvalidCredentialsError(AuthError):
    """Credenciales inválidas."""


class InvalidTokenError(AuthError):
    """Token inválido o expirado."""


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: Literal["admin", "user"]


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


class AuthService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def authenticate(self, username: str, password: str) -> AuthUser:
        if (
            username == self.settings.admin_username
            and password == self.settings.admin_password
        ):
            return AuthUser(username=username, role="admin")
        if (
            username == self.settings.normal_username
            and password == self.settings.normal_password
        ):
            return AuthUser(username=username, role="user")
        raise InvalidCredentialsError("Usuario o contraseña inválidos.")

    def create_access_token(self, user: AuthUser) -> tuple[str, int]:
        expires_in = self.settings.auth_token_expire_minutes * 60
        expires_at = int(
            (datetime.now(UTC) + timedelta(seconds=expires_in)).timestamp()
        )
        payload = {
            "sub": user.username,
            "role": user.role,
            "exp": expires_at,
        }
        payload_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        payload_encoded = _b64url_encode(payload_bytes)
        signature = self._sign(payload_encoded)
        return f"{payload_encoded}.{signature}", expires_in

    def verify_token(self, token: str) -> AuthUser:
        try:
            payload_encoded, signature = token.split(".", maxsplit=1)
        except ValueError as exc:
            raise InvalidTokenError("El token no tiene un formato válido.") from exc

        expected_signature = self._sign(payload_encoded)
        if not hmac.compare_digest(signature, expected_signature):
            raise InvalidTokenError("La firma del token no es válida.")

        try:
            payload = json.loads(_b64url_decode(payload_encoded).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidTokenError("No se pudo decodificar el token.") from exc

        if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
            raise InvalidTokenError("La sesión expiró. Inicia sesión nuevamente.")

        username = str(payload.get("sub", "")).strip()
        role = str(payload.get("role", "")).strip()
        if role not in {"admin", "user"} or not username:
            raise InvalidTokenError("El token no contiene un usuario válido.")
        return AuthUser(username=username, role=role)

    def _sign(self, payload_encoded: str) -> str:
        digest = hmac.new(
            self.settings.auth_secret_key.encode("utf-8"),
            payload_encoded.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return _b64url_encode(digest)
