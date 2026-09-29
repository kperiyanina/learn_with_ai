from fastapi import APIRouter, HTTPException

from backend_api.dependencies import UserId
from backend_api.schemas import (
    Credentials,
    ProfileResponse,
    ProfileUpdate,
    TokenResponse,
)
from security.tokens import create_access_token
from storage.database import (
    authenticate_user,
    get_profile,
    register_user,
    update_profile,
)


router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(credentials: Credentials) -> TokenResponse:
    try:
        user = register_user(credentials.email, credentials.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/auth/login", response_model=TokenResponse)
def login(credentials: Credentials) -> TokenResponse:
    try:
        user = authenticate_user(credentials.email, credentials.password)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/users/me", response_model=ProfileResponse)
def get_current_profile(user_id: UserId) -> ProfileResponse:
    try:
        profile = get_profile(user_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ProfileResponse(**profile.__dict__)


@router.patch("/users/me", response_model=ProfileResponse)
def edit_current_profile(
    update: ProfileUpdate,
    user_id: UserId,
) -> ProfileResponse:
    try:
        update_profile(user_id, update.display_name)
        profile = get_profile(user_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ProfileResponse(**profile.__dict__)
