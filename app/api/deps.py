from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.schemas.auth import CurrentUserResponse
from app.services.auth_service import AuthService, AuthUser, InvalidTokenError


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "").strip()
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesión para acceder a este recurso.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", maxsplit=1)[1].strip()


def get_current_user(request: Request) -> AuthUser:
    if hasattr(request.state, "current_user"):
        return request.state.current_user

    token = _extract_bearer_token(request)
    try:
        user = AuthService().verify_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    request.state.current_user = user
    return user


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este recurso está disponible solo para administradores.",
        )
    return user


def require_user(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este recurso está disponible solo para usuarios finales.",
        )
    return user
