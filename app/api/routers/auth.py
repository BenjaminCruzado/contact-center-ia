from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.schemas.auth import AuthTokenResponse, CurrentUserResponse, LoginRequest
from app.services.auth_service import AuthService, AuthUser, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    payload: LoginRequest,
    request: Request,
) -> AuthTokenResponse:
    service = AuthService()
    try:
        user = service.authenticate(payload.username, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    token, expires_in = service.create_access_token(user)
    request.state.audit_context = {
        "interaction_type": "auth",
        "status": "processed",
        "metadata": {"role": user.role},
    }
    return AuthTokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        expires_in_seconds=expires_in,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
)
async def me(current_user: AuthUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        username=current_user.username,
        role=current_user.role,
    )
