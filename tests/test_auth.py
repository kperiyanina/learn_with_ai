import unittest

from security.passwords import hash_password, validate_credentials, verify_password


class AuthTest(unittest.TestCase):
    def test_password_hash_can_be_verified(self):
        salt, password_hash = hash_password("correct-password")

        self.assertTrue(verify_password("correct-password", salt, password_hash))
        self.assertFalse(verify_password("wrong-password", salt, password_hash))

    def test_credentials_require_valid_email_and_password(self):
        with self.assertRaisesRegex(
            ValueError, "корректный адрес электронной почты"
        ):
            validate_credentials("not-an-email", "correct-password")

        with self.assertRaisesRegex(
            ValueError, "не менее 8 символов"
        ):
            validate_credentials("user@example.com", "short")


if __name__ == "__main__":
    unittest.main()
