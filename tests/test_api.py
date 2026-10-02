import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

import api
from storage import database


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        database.DATABASE_PATH = Path(cls.temp_dir) / "test.db"
        database.init_database()
        cls.client = TestClient(api.app)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def test_health_endpoint_is_public(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_register_login_and_profile_are_available(self):
        email = "api-user@example.com"
        password = "correct-password"

        register_response = self.client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        self.assertEqual(register_response.status_code, 201)
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        profile_response = self.client.get("/users/me", headers=headers)
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()["display_name"], "")

        update_response = self.client.patch(
            "/users/me",
            headers=headers,
            json={"display_name": "API пользователь"},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["display_name"],
            "API пользователь",
        )

        login_response = self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(login_response.status_code, 200)

    def test_private_endpoints_require_authentication(self):
        response = self.client.get("/plans")

        self.assertEqual(response.status_code, 401)

    def test_private_endpoints_reject_invalid_token(self):
        response = self.client.get(
            "/plans",
            headers={"Authorization": "Bearer " + "invalid-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Недействительный токен доступа.")

    def test_invalid_plan_is_rejected_before_ai(self):
        email = f"invalid-{uuid.uuid4().hex}@example.com"
        token = self.client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "correct-password",
            },
        ).json()["access_token"]
        token = self.client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "correct-password",
            },
        ).json()["access_token"]

        response = self.client.post(
            "/plans",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "goal": "12345",
                "level": "Начинающий",
                "weeks": 4,
                "hours_per_week": 5,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("только из цифр", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
