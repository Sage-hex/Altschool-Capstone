from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def create_user(db: Session, *, name: str, email: str, hashed_password: str, role: str) -> User:
    user = User(name=name, email=email.lower(), hashed_password=hashed_password, role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
