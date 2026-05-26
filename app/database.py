"""SQLAlchemy engine, session factory, and declarative base for the project."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

if DATABASE_URL.startswith("sqlite:///"):
    _db_path = DATABASE_URL.removeprefix("sqlite:///")
    if _db_path and not _db_path.startswith(":memory:"):
        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

_connect_args: dict[str, object] = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a Session and closes it after the request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
