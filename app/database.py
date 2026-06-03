from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path


def connect(database_url: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_url, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    migrate(connection)
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'admin')) DEFAULT 'student',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            instructor TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK (capacity > 0),
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'cancelled')) DEFAULT 'active',
            enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, course_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """
    )
    connection.commit()


def database_path_from_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.removeprefix("sqlite:///")
    if database_url == ":memory:":
        return database_url
    return str(Path(database_url))


def get_connection(connection: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    yield connection


COURSE_SELECT = """
    SELECT
        c.*,
        COUNT(CASE WHEN e.status = 'active' THEN 1 END) AS enrollment_count,
        c.capacity - COUNT(CASE WHEN e.status = 'active' THEN 1 END) AS available_seats
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
"""

ENROLLMENT_SELECT = """
    SELECT
        e.id,
        e.status,
        e.enrolled_at AS enrolled_at,
        e.updated_at AS updated_at,
        u.id AS user_id,
        u.name AS user_name,
        u.email AS user_email,
        c.id AS course_id,
        c.title AS course_title,
        c.instructor AS course_instructor
    FROM enrollments e
    JOIN users u ON u.id = e.user_id
    JOIN courses c ON c.id = e.course_id
"""
