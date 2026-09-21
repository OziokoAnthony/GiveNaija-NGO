from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import hmac
import hashlib
import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: str,
    role: str,
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Issue a signed JWT access token containing subject (email), role, and user_id.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "user_id": user_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns the payload dictionary if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify payment provider HMAC-SHA256 signature using constant-time comparison.
    Header: X-Signature: HMAC-SHA256(secret, raw_body), hex
    Must use hmac.compare_digest to prevent timing attacks.
    """
    if not signature or not secret:
        return False
    computed = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def verify_cron_api_key(api_key: str) -> bool:
    """
    Verify the cron/scheduled trigger API key using constant-time comparison.
    """
    if not api_key:
        return False
    return hmac.compare_digest(api_key, settings.CRON_API_KEY)
