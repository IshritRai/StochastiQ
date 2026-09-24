"""Managed Postgres providers (Render, Railway, etc.) hand out a plain
postgres:// or postgresql:// connection string; SQLAlchemy defaults that
scheme to psycopg2, which this project doesn't install. Settings rewrites
it to the psycopg (v3) driver that's actually a dependency, so a provider's
URL works unmodified.
"""

from __future__ import annotations

from app.config import Settings


def test_postgres_scheme_rewritten_to_psycopg_driver():
    s = Settings(database_url="postgres://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_postgresql_scheme_rewritten_to_psycopg_driver():
    s = Settings(database_url="postgresql://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_explicit_driver_scheme_left_untouched():
    s = Settings(database_url="postgresql+psycopg://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_sqlite_url_left_untouched():
    s = Settings(database_url="sqlite:///./stochastiq.db")
    assert s.database_url == "sqlite:///./stochastiq.db"
