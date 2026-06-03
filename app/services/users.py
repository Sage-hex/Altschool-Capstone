from __future__ import annotations

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import users as user_repo
from app.security import create_access_token, hash_password, verify_password
from app.services.errors import api_error


def register_user(db: Session, *, name: str, email: str, password: str, role: str, jwt_secret: str) -> dict[str, object]:
    try:
        user = user_repo.create_user(db, name=name.strip(), email=email.lower(), hashed_password=hash_password(password), role=role)
    except IntegrityError as error:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_REGISTERED", "A user with this email already exists.") from error
    return {"user": user, "token": create_access_token({"sub": user.id, "role": user.role}, jwt_secret)}


def authenticate_user(db: Session, *, email: str, password: str, jwt_secret: str) -> dict[str, object]:
    user = user_repo.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    if not user.is_active:
        raise api_error(status.HTTP_403_FORBIDDEN, "USER_INACTIVE", "Inactive users cannot authenticate.")
    return {"user": user, "token": create_access_token({"sub": user.id, "role": user.role}, jwt_secret)}


def require_active_user(user: User) -> User:
    if not user.is_active:
        raise api_error(status.HTTP_403_FORBIDDEN, "USER_INACTIVE", "Inactive users cannot use this API.")
    return user
