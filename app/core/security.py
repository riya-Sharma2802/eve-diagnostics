import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


# ---- passwords -------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---- JWT -------------------------------------------------------------------
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> int | None:
    """Return the user id from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if isinstance(sub, str) and sub.isdigit():
        return int(sub)
    return None


# ---- webhook signatures ----------------------------------------------------
def sign_payload(body: bytes) -> str:
    return hmac.new(
        settings.webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()


def verify_signature(body: bytes, signature: str) -> bool:
    expected = sign_payload(body)
    return hmac.compare_digest(expected.encode("utf-8"), signature.encode("utf-8"))
