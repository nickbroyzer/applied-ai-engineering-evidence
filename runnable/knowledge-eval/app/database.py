"""Engine and Base for the knowledge-eval package.

Binds to DATABASE_URL, which conftest.py sets from TEST_DATABASE_URL before
any app module is imported — the same discipline the production test suite
uses (`backend/tests/conftest.py`), so a misconfigured run cannot reach a
real database.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_URL = os.environ.get("DATABASE_URL", "")
if not _URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Run through pytest (conftest.py sets it from "
        "TEST_DATABASE_URL), or export it before invoking a script directly."
    )

# psycopg v3 is what requirements.txt pins; a bare postgresql:// URL would try
# psycopg2. The production config does the same rewrite.
if _URL.startswith("postgresql://"):
    _URL = _URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()
