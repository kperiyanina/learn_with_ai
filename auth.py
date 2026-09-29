import hashlib
import hmac
import secrets


HASH_ITERATIONS = 600_000


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return salt, password_hash


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return hmac.compare_digest(actual_hash, expected_hash)


def validate_credentials(email: str, password: str) -> None:
    if not isinstance(email, str) or not email.strip():
        raise ValueError("Введите электронную почту.")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Введите корректный адрес электронной почты.")
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов.")
