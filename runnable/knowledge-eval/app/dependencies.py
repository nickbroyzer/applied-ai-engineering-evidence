"""Request-scoped database session. The production file also carries the
Supabase JWT verification chain, which this package does not need."""
from typing import Iterator

from app.database import SessionLocal


def get_db() -> Iterator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
