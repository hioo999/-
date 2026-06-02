"""用户认证与会话 API。"""

from __future__ import annotations

import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models.persona import AuthSession, UserAccount
from services.auth_security import hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["用户认证"])


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("邮箱格式不正确")
        return email


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200, description="邮箱或管理员账号 admin")
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_account(cls, value: str) -> str:
        email = value.strip().lower()
        if email == "admin":
            return os.getenv("ADMIN_EMAIL", "admin@163.com").strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("请输入邮箱，或使用管理员账号 admin")
        return email


def _hash_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_session(db: Session, user: UserAccount) -> dict:
    token = secrets.token_urlsafe(40)
    session = AuthSession(user_id=user.id, token_hash=_hash_token(token))
    db.add(session)
    db.commit()
    return {"token": token, "user": user.to_public_dict()}


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> UserAccount:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录后再使用该功能")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证无效")

    session = db.query(AuthSession).filter(
        AuthSession.token_hash == _hash_token(token),
        AuthSession.revoked_at.is_(None),
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")

    user = db.query(UserAccount).filter(
        UserAccount.id == session.user_id,
        UserAccount.is_active.is_(True),
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已被停用")
    return user


def get_admin_user(user: UserAccount = Depends(get_current_user)) -> UserAccount:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


@router.post("/register", summary="注册账号")
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = data.email.lower()
    existing = db.query(UserAccount).filter(UserAccount.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    user = UserAccount(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 0, "data": _issue_session(db, user)}


@router.post("/login", summary="登录")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.lower()
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码不正确")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    return {"code": 0, "data": _issue_session(db, user)}


@router.get("/me", summary="获取当前登录用户")
async def me(user: UserAccount = Depends(get_current_user)):
    return {"code": 0, "data": {"user": user.to_public_dict()}}


@router.post("/logout", summary="退出登录")
async def logout(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        session = db.query(AuthSession).filter(AuthSession.token_hash == _hash_token(token)).first()
        if session and not session.revoked_at:
            session.revoked_at = datetime.utcnow()
            db.commit()
    return {"code": 0, "message": "已退出登录"}
