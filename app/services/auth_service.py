import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.auth import SignupRequest

logger = logging.getLogger(__name__)


def signup(db: Session, data: SignupRequest) -> User:
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two signups racing with the same email
        db.rollback()
        raise ConflictError("Email already registered")
    db.refresh(user)
    logger.info("user_signed_up user_id=%s", user.id)
    return user


def login(db: Session, email: str, password: str) -> str:
    user = db.scalar(select(User).where(User.email == email.lower()))
    # Same message for unknown email and wrong password (no user enumeration).
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    return create_access_token(user.id)
