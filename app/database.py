from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def create_engine_for_url(database_url: str) -> Engine:
    database_url = normalize_database_url(database_url)
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    connect_args: dict[str, object] = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url.endswith(":memory:"):
            engine_options["poolclass"] = StaticPool

    engine = create_engine(database_url, connect_args=connect_args, **engine_options)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(database_url: str) -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine_for_url(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False), engine


def init_database(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def get_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
