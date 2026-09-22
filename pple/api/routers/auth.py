"""
FastAPI Router for User Authentication & Authorization (PPLE Agent V2)
Provides endpoints for login, session check (/me), password updates, and logout.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from src.auth import (
    authenticate_user,
    change_user_password,
    generate_token,
    get_user_by_username,
    verify_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def get_current_user_payload(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to extract and verify the bearer token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header otentikasi tidak ditemukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format token otentikasi harus: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = parts[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi telah kedaluwarsa atau token tidak valid. Silakan login kembali.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


@router.post("/login")
def login(req: LoginRequest):
    """Verifies username & password; returns secure session token and user profile."""
    username = (req.username or "").strip()
    password = req.password or ""
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username dan kata sandi wajib diisi.",
        )

    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau kata sandi tidak sesuai. Silakan periksa kembali.",
        )

    token = generate_token(user, expires_hours=168)  # 7 days
    return {
        "status": "success",
        "message": f"Selamat datang, {user['full_name']}!",
        "token": token,
        "user": user,
    }


@router.get("/me")
def get_me(payload: dict = Depends(get_current_user_payload)):
    """Returns current active authenticated user profile."""
    username = payload.get("sub", "")
    full_user = get_user_by_username(username)
    if not full_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil pengguna tidak ditemukan.",
        )

    return {
        "authenticated": True,
        "user": {
            "username": full_user["username"],
            "full_name": full_user.get("full_name", full_user["username"]),
            "role": full_user.get("role", "OPERATOR"),
            "unit": full_user.get("unit", "PLTU Jeranjang"),
            "title": full_user.get("title", "Plant Personnel"),
        },
    }


@router.post("/logout")
def logout():
    """Client-side token invalidation confirmation."""
    return {"status": "success", "message": "Sesi berhasil diakhiri."}


@router.post("/change-password")
def update_password(req: ChangePasswordRequest, payload: dict = Depends(get_current_user_payload)):
    """Updates user password."""
    username = payload.get("sub", "")
    ok, msg = change_user_password(username, req.old_password, req.new_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg}
