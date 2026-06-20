from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
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
from ..security import client_identity, enforce_rate_limit, hash_token, token_blacklist
from ..session_store import session_store

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
    refresh_token, expires_at = create_refresh_token()
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=expires_at.replace(tzinfo=None),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    session_id = session_store.create_session(
        user_id=user.id,
        refresh_token_id=record.id,
        ttl_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    access_token = create_access_token(user.id, session_id=session_id)
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "sessionId": session_id,
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
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    enforce_rate_limit("auth.login", client_identity(request))
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

    session = session_store.find_active_session_by_refresh_token(record.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_revoked", "message": "当前登录会话已失效，请重新登录。"},
        )
    access_token = create_access_token(record.user_id, session_id=str(session.get("sessionId") or ""))
    return {
        "accessToken": access_token,
        "tokenType": "bearer",
        "user": user_response(record.user),
    }


@router.post("/logout")
async def logout(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    token_hash = hash_refresh_token(payload.refreshToken)
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()
    if record and not record.revoked_at:
        record.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        session = session_store.find_active_session_by_refresh_token(record.id)
        if session:
            session_store.revoke_session(str(session.get("sessionId") or ""), reason="logout")
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1].strip()
        if access_token:
            token_blacklist.add(hash_token(access_token), ttl_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return user_response(current_user)
