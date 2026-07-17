from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_active_user
from auth.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token as generate_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
)
from database.connection import get_db
from database.crud import (
    create_refresh_token as store_refresh_token,
    create_user,
    get_refresh_token_by_hash,
    get_user_by_email,
    get_user_by_id,
    revoke_refresh_token,
)
from database.models import User
from backend.api.schemas.auth import Token, TokenRefresh, UserCreate, UserLogin, UserResponse
from services.rate_limiter import (
    check_login_rate_limit,
    check_register_rate_limit,
    record_login_failure,
    record_register_failure,
    reset_login_failures,
    reset_register_failures,
)

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    await check_register_rate_limit(body.email)
    existing = await get_user_by_email(db, body.email)
    if existing:
        await record_register_failure(body.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await create_user(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
    )
    await reset_register_failures(body.email)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    await check_login_rate_limit(body.email)
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        await record_login_failure(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    await reset_login_failures(body.email)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = generate_refresh_token(data={"sub": str(user.id)})
    await store_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh(body: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    token_hash = hash_refresh_token(body.refresh_token)
    db_token = await get_refresh_token_by_hash(db, token_hash)
    if db_token is None or db_token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or not found",
        )
    if db_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    new_access_token = create_access_token(data={"sub": payload["sub"]})
    return Token(
        access_token=new_access_token,
        refresh_token=body.refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    body: TokenRefresh,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_refresh_token(body.refresh_token)
    db_token = await get_refresh_token_by_hash(db, token_hash)
    if db_token and db_token.user_id == current_user.id:
        await revoke_refresh_token(db, db_token.id)
    return {"message": "Logged out successfully"}
