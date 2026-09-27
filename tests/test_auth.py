"""
Unit tests for PPLE Auth Module and FastAPI Auth Router.
Verifies PBKDF2 password hashing, bearer token signing/verification, and API endpoints.
"""

import unittest
from fastapi.testclient import TestClient

from api_server import app
from src.auth import (
    authenticate_user,
    change_user_password,
    generate_token,
    get_user_by_username,
    hash_password,
    update_user_avatar,
    verify_password,
    verify_token,
)

TINY_PNG_DATA_URL = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
    "2mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


class AuthCoreTests(unittest.TestCase):
    def test_password_hashing_and_verification(self):
        pwd = "SecretPlantPassword#2026"
        stored = hash_password(pwd)
        parts = stored.split(":")
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[0]), 32)  # 16-byte salt in hex
        self.assertEqual(len(parts[1]), 64)  # 32-byte SHA-256 in hex
        self.assertTrue(verify_password(pwd, stored))
        self.assertFalse(verify_password("WrongPassword", stored))

    def test_seeded_users_exist(self):
        admin = get_user_by_username("admin")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "ADMIN")

        eng = get_user_by_username("engineer")
        self.assertIsNotNone(eng)
        self.assertEqual(eng["role"], "ENGINEER")

        op = get_user_by_username("operator")
        self.assertIsNotNone(op)
        self.assertEqual(op["role"], "OPERATOR")

    def test_authenticate_user(self):
        user = authenticate_user("admin", "admin2026")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")
        self.assertNotIn("password_hash", user)

        # Wrong password
        self.assertIsNone(authenticate_user("admin", "wrong_pass"))
        # Non-existent user
        self.assertIsNone(authenticate_user("unknown_user_99", "admin2026"))

    def test_token_lifecycle(self):
        user = {"username": "engineer", "role": "ENGINEER"}
        token = generate_token(user, expires_hours=1)
        self.assertIsInstance(token, str)

        payload = verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "engineer")
        self.assertEqual(payload.get("role"), "ENGINEER")

        # Tampered token
        tampered = token[:-4] + "abcd"
        self.assertIsNone(verify_token(tampered))

        # Expired token (negative hours)
        expired_token = generate_token(user, expires_hours=-1)
        self.assertIsNone(verify_token(expired_token))

    def test_update_user_avatar(self):
        try:
            ok, msg = update_user_avatar("operator", TINY_PNG_DATA_URL)
            self.assertTrue(ok, msg)
            self.assertEqual(get_user_by_username("operator")["avatar"], TINY_PNG_DATA_URL)

            # Clearing sets it back to None
            ok, _ = update_user_avatar("operator", None)
            self.assertTrue(ok)
            self.assertIsNone(get_user_by_username("operator")["avatar"])

            # Rejects non-image data URLs and oversized payloads
            ok, _ = update_user_avatar("operator", "data:text/plain;base64,aGVsbG8=")
            self.assertFalse(ok)
            ok, _ = update_user_avatar("operator", "data:image/png;base64," + ("A" * 400_000))
            self.assertFalse(ok)
        finally:
            update_user_avatar("operator", None)


class AuthApiRouterTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_login_success_and_me(self):
        res = self.client.post("/api/auth/login", json={"username": "engineer", "password": "cbm2026"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], "engineer")

        token = data["token"]
        # Call /api/auth/me with Bearer token
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()
        self.assertTrue(me_data["authenticated"])
        self.assertEqual(me_data["user"]["username"], "engineer")
        self.assertEqual(me_data["user"]["role"], "ENGINEER")

    def test_login_failure(self):
        res = self.client.post("/api/auth/login", json={"username": "engineer", "password": "wrongpassword"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("detail", res.json())

    def test_me_unauthorized(self):
        # Without header
        res1 = self.client.get("/api/auth/me")
        self.assertEqual(res1.status_code, 401)

        # With invalid token
        res2 = self.client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
        self.assertEqual(res2.status_code, 401)

    def test_logout(self):
        res = self.client.post("/api/auth/logout")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

    def test_avatar_update_requires_auth(self):
        res = self.client.post("/api/auth/avatar", json={"avatar": TINY_PNG_DATA_URL})
        self.assertEqual(res.status_code, 401)

    def test_avatar_set_appears_in_login_and_me(self):
        login = self.client.post("/api/auth/login", json={"username": "operator", "password": "operator2026"})
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        try:
            res = self.client.post("/api/auth/avatar", json={"avatar": TINY_PNG_DATA_URL}, headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["user"]["avatar"], TINY_PNG_DATA_URL)

            me_res = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(me_res.json()["user"]["avatar"], TINY_PNG_DATA_URL)

            login2 = self.client.post("/api/auth/login", json={"username": "operator", "password": "operator2026"})
            self.assertEqual(login2.json()["user"]["avatar"], TINY_PNG_DATA_URL)

            # Invalid payload is rejected with 400
            bad_res = self.client.post("/api/auth/avatar", json={"avatar": "not-a-data-url"}, headers=headers)
            self.assertEqual(bad_res.status_code, 400)
        finally:
            update_user_avatar("operator", None)


if __name__ == "__main__":
    unittest.main()
