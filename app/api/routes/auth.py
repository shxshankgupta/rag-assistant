from typing import Annotated

from fastapi import APIRouter, Depends
from jose import JWTError

from app.api.deps import CurrentUser, enforce_api_rate_limit, get_user_service
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.auth import (
    PasswordChange,
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserCreate,
    user_svc: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create a new user account."""
    user = await user_svc.create_user(data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    user_svc: UserService = Depends(get_user_service),
) -> TokenResponse:
    """Authenticate and receive access + refresh tokens."""
    user = await user_svc.authenticate(data.username, data.password)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefresh,
    user_svc: UserService = Depends(get_user_service),
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Not a refresh token")
        user_id: str = payload["sub"]
    except JWTError as e:
        raise UnauthorizedError(f"Invalid refresh token: {e}")

    user = await user_svc.get_by_id(user_id)
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse, dependencies=[Depends(enforce_api_rate_limit)])
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", status_code=204, dependencies=[Depends(enforce_api_rate_limit)])
async def change_password(
    data: PasswordChange,
    current_user: CurrentUser,
    user_svc: UserService = Depends(get_user_service),
) -> None:
    """Change the authenticated user's password."""
    await user_svc.change_password(
        current_user, data.current_password, data.new_password
    )
