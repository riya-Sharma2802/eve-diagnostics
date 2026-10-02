from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token, verify_signature
from app.models.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise UnauthorizedError("Not authenticated")
    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        raise UnauthorizedError("Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise ForbiddenError("Admin access required")
    return user


async def verified_webhook_body(
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
) -> bytes:
    """Read the raw body and check the provider's HMAC signature."""
    body = await request.body()
    if not x_webhook_signature or not verify_signature(body, x_webhook_signature):
        raise UnauthorizedError("Invalid webhook signature")
    return body
