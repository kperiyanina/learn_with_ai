import base64
import hashlib
import hmac
import json
import time

from core.config import API_SECRET_KEY


TOKEN_TTL_SECONDS = 60 * 60 * 24


def create_access_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "expires_at": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")))
    signature = hmac.new(
        API_SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def get_user_id_from_token(token: str) -> int:
    try:
        encoded_payload, signature = token.split(".", 1)
        expected_signature = hmac.new(
            API_SECRET_KEY.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError

        payload = json.loads(_decode(encoded_payload))
        if int(payload["expires_at"]) < int(time.time()):
            raise ValueError
        return int(payload["user_id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("Недействительный токен доступа.") from error


def _encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii")).decode("utf-8")
