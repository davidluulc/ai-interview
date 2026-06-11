from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    create_refresh_token,
    find_user_by_email,
    get_current_user,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from ..database import get_db
from ..db_models import RefreshToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserCreateRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str = "user"


def user_response(user: User) -> dict:
    return {"id": user.id, "email": user.email, "username": user.username, "role": user.role}


def token_response(db: Session, user: User) -> dict:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at.replace(tzinfo=None),
        )
    )
    db.commit()
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "bearer",
        "user": user_response(user),
    }


@router.post("/register", response_model=UserResponse)
async def register(payload: UserCreateRequest, db: Session = Depends(get_db)) -> dict:
    email = payload.email.lower()
    existing = db.scalars(
        select(User).where(or_(User.email == email, User.username == payload.username))
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already registered")

    user = User(
        email=email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.post("/login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = find_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return token_response(db, user)


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    token_hash = hash_refresh_token(payload.refreshToken)
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not record or record.revoked_at or record.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = create_access_token(record.user_id)
    return {
        "accessToken": access_token,
        "tokenType": "bearer",
        "user": user_response(record.user),
    }


@router.post("/logout")
async def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    token_hash = hash_refresh_token(payload.refreshToken)
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if record and not record.revoked_at:
        record.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return user_response(current_user)
