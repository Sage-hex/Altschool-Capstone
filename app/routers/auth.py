from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import TokenResponse, UserCreate, UserLogin, UserOut
from app.services.users import authenticate_user, register_user

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    return register_user(db, name=payload.name, email=payload.email, password=payload.password, role=payload.role, jwt_secret=request.app.state.jwt_secret)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLogin, request: Request, db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    return authenticate_user(db, email=payload.email, password=payload.password, jwt_secret=request.app.state.jwt_secret)


@router.get("/users/me", response_model=dict[str, UserOut])
def me(user: Annotated[User, Depends(get_current_user)]) -> dict[str, User]:
    return {"user": user}
