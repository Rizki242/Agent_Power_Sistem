"""
PPLE Agent - User Authentication & Session Security Module
Implements PBKDF2-HMAC-SHA256 password hashing, cryptographically signed
bearer tokens, and role-based access for PLTU Jeranjang personnel.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SECRET_KEY_FILE = os.path.join(DATA_DIR, "auth_secret.key")


def _get_or_create_secret_key() -> bytes:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SECRET_KEY_FILE):
        try:
            with open(SECRET_KEY_FILE, "rb") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        except Exception:
            pass
    # Generate 32-byte cryptographically secure key
    new_key = secrets.token_bytes(32)
    try:
        with open(SECRET_KEY_FILE, "wb") as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key


MAX_AVATAR_DATA_URL_LENGTH = 300_000  # ~220 KB decoded, enough for a small square thumbnail
ALLOWED_AVATAR_MIME_TYPES = ("image/png", "image/jpeg", "image/webp")


def hash_password(password: str) -> str:
    """Hash password with PBKDF2-HMAC-SHA256 using random 16-byte salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt:hash string."""
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(hash_hex)
        computed_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(computed_dk, expected_dk)
    except Exception:
        return False


def _get_default_users() -> List[Dict[str, Any]]:
    return [
        {
            "username": "admin",
            "password_hash": hash_password("admin2026"),
            "full_name": "Manager Pemeliharaan & Keandalan",
            "role": "ADMIN",
            "unit": "All Units (3 × 25 MW)",
            "title": "Reliability & Maintenance Lead",
            "created_at": "2026-01-01T00:00:00",
            "active": True,
        },
        {
            "username": "engineer",
            "password_hash": hash_password("cbm2026"),
            "full_name": "CBM & Predictive Maintenance Engineer",
            "role": "ENGINEER",
            "unit": "Unit 1, 2, 3 & BOP",
            "title": "Condition Monitoring Specialist",
            "created_at": "2026-01-01T00:00:00",
            "active": True,
        },
        {
            "username": "operator",
            "password_hash": hash_password("operator2026"),
            "full_name": "Operator Lapangan & Walkdown",
            "role": "OPERATOR",
            "unit": "Unit 1 Main Power Block",
            "title": "Field Operations Inspector",
            "created_at": "2026-01-01T00:00:00",
            "active": True,
        },
    ]


def load_users() -> List[Dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        defaults = _get_default_users()
        save_users(defaults)
        return defaults
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception:
        pass
    defaults = _get_default_users()
    save_users(defaults)
    return defaults


def save_users(users: List[Dict[str, Any]]) -> bool:
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except Exception as exc:
        print(f"[Auth] Gagal menyimpan users.json: {exc}")
        return False


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    clean = (username or "").strip().lower()
    users = load_users()
    for u in users:
        if u.get("username", "").lower() == clean and u.get("active", True):
            return u
    return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify credentials; return sanitized user dictionary on success, None on failure."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None

    # Return safe user dictionary without password hash
    return {
        "username": user["username"],
        "full_name": user.get("full_name", user["username"]),
        "role": user.get("role", "OPERATOR"),
        "unit": user.get("unit", "PLTU Jeranjang"),
        "title": user.get("title", "Plant Personnel"),
        "avatar": user.get("avatar"),
    }


def generate_token(user: Dict[str, Any], expires_hours: int = 168) -> str:
    """Generate cryptographically signed base64 session token."""
    secret_key = _get_or_create_secret_key()
    payload = {
        "sub": user["username"],
        "role": user.get("role", "OPERATOR"),
        "name": user.get("full_name", user["username"]),
        "exp": int(time.time()) + (expires_hours * 3600),
        "iat": int(time.time()),
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")

    signature = hmac.new(secret_key, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify signed session token. Returns payload dict on success, None on invalid/expired."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        secret_key = _get_or_create_secret_key()

        # Check signature with constant-time comparison
        expected_sig = hmac.new(secret_key, payload_b64.encode("utf-8"), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        # Decode payload
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def change_user_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    if not new_password or len(new_password) < 6:
        return False, "Kata sandi baru minimal 6 karakter."

    users = load_users()
    clean = username.strip().lower()
    for u in users:
        if u.get("username", "").lower() == clean:
            if not verify_password(old_password, u.get("password_hash", "")):
                return False, "Kata sandi lama tidak sesuai."
            u["password_hash"] = hash_password(new_password)
            u["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            save_users(users)
            return True, "Kata sandi berhasil diperbarui."
    return False, "Pengguna tidak ditemukan."


def update_user_avatar(username: str, avatar_data_url: Optional[str]) -> Tuple[bool, str]:
    """Set or clear a user's profile photo (a small base64 data: URL) in users.json.

    `avatar_data_url` of None/"" clears the photo. Otherwise it must be a
    `data:image/<png|jpeg|webp>;base64,...` string within MAX_AVATAR_DATA_URL_LENGTH,
    since it is stored inline rather than as a separate uploaded file.
    """
    if avatar_data_url:
        if len(avatar_data_url) > MAX_AVATAR_DATA_URL_LENGTH:
            return False, "Ukuran foto terlalu besar. Gunakan foto yang lebih kecil."
        if not avatar_data_url.startswith("data:"):
            return False, "Format foto tidak valid."
        header = avatar_data_url.split(",", 1)[0]
        if not any(header.startswith(f"data:{mime};base64") for mime in ALLOWED_AVATAR_MIME_TYPES):
            return False, "Format foto harus PNG, JPEG, atau WEBP."

    users = load_users()
    clean = username.strip().lower()
    for u in users:
        if u.get("username", "").lower() == clean:
            u["avatar"] = avatar_data_url or None
            u["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            save_users(users)
            return True, "Foto profil berhasil diperbarui."
    return False, "Pengguna tidak ditemukan."

