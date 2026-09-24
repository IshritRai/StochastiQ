"""Engine/session wiring. SQLite locally, Postgres-compatible via SQLAlchemy."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.data.models import Base

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
# expire_on_commit=False: callers (esp. dashboard pages) routinely read ORM
# objects returned from a `with session_scope():` block after it has closed
# and committed. Without this, every attribute access after commit would
# need to re-open a session (DetachedInstanceError otherwise).
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False
)


def init_db() -> None:
    """Create all tables. Idempotent: safe to call every `make seed` run."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
