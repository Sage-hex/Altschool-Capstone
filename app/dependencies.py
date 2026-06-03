from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import User
from app.repositories.users import get_user_by_id
from app.security import decode_access_token
from app.services.errors import api_error
from app.services.users import require_active_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db(request: Request) -> Generator[Session, None, None]:
    yield from get_session(request.app.state.session_factory)


def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    payload = decode_access_token(token, request.app.state.jwt_secret)
    if not payload or "sub" not in payload:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "A valid bearer token is required.")
    user = get_user_by_id(db, int(payload["sub"]))
    if user is None:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "A valid bearer token is required.")
    return require_active_user(user)


def require_role(role: str):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role != role:
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", f"Only {role}s can perform this action.")
        return user

    return dependency
