"""pytest configuration for the standalone knowledge-eval package.

Mirrors the discipline of the private repository's `backend/tests/conftest.py`:
hard-fail before any app module is imported if TEST_DATABASE_URL is unset or
identical to DATABASE_URL, then override DATABASE_URL in-process so every
module binds to the test database and cannot reach a real one.

Two deliberate differences from the private conftest:

- Schema comes from `Base.metadata.create_all()` rather than `alembic upgrade
  head`. This package ships the six knowledge models, not the 44-revision
  migration history, and the tables they produce are the same.
- No Stripe, auth, or rate-limit fixtures: this package contains none of that.
"""
import os
import sys
from typing import Iterator

_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
_PROD_DB_URL = os.environ.get("DATABASE_URL", "").strip()


def _fail_env(reason: str) -> None:
    sys.stderr.write(
        "\n"
        f"FATAL: {reason}\n"
        "\n"
        "This package must run against a database you are willing to have\n"
        "truncated between tests.\n"
        "\n"
        "Setup:\n"
        "  1. createdb knowledge_eval_test\n"
        "     psql -d knowledge_eval_test -c 'CREATE EXTENSION \"uuid-ossp\";'\n"
        "\n"
        "  2. export TEST_DATABASE_URL='postgresql://localhost/knowledge_eval_test'\n"
        "\n"
        "  3. pytest\n"
        "\n"
        "PostgreSQL is required and PostGIS is not: retrieval uses full-text\n"
        "search (to_tsvector / websearch_to_tsquery / ts_rank) and array\n"
        "containment, none of which SQLite provides.\n"
    )
    raise SystemExit(2)


if not _TEST_DB_URL:
    _fail_env("TEST_DATABASE_URL is not set.")
if _TEST_DB_URL == _PROD_DB_URL:
    _fail_env("TEST_DATABASE_URL is identical to DATABASE_URL.")

os.environ["DATABASE_URL"] = _TEST_DB_URL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.dependencies import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.routers.admin import require_admin  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

_DOMAIN_TABLES = (
    "knowledge_query_logs",
    "knowledge_eval_runs",
    "knowledge_eval_cases",
    "knowledge_chunks",
    "knowledge_documents",
    "knowledge_ingestion_runs",
    "users",
)


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(_DOMAIN_TABLES)} CASCADE"))


@pytest.fixture
def db_session(_clean_tables) -> Iterator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(db_session):
    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.pop(get_db, None)
    fastapi_app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(app, client):
    """Supply a caller to the CX route's admin gate.

    Mirrors the private suite's fixture of the same name: the gate refuses by
    default (401), and a test that wants a caller asks for one. A non-admin
    caller still gets 403 — the authorization half of the gate is real, only
    the authentication half is stubbed.
    """
    def _as(user):
        def _override():
            if not user.is_admin:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Admin required"
                )
            return user

        app.dependency_overrides[require_admin] = _override
        return client

    return _as


def _make_user(db_session, *, is_admin: bool):
    import uuid as _uuid

    user = models.User(
        email=f"u+{_uuid.uuid4().hex[:8]}@example.com",
        display_name="Admin" if is_admin else "Picker",
        is_admin=is_admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    return _make_user(db_session, is_admin=True)


@pytest.fixture
def picker_user(db_session):
    return _make_user(db_session, is_admin=False)
