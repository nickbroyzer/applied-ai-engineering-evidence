from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# prepare_threshold=None disables psycopg v3's automatic server-side prepared
# statements. Production connects through Supabase's transaction-mode pooler
# (port 6543), where one backend connection is shared between callers between
# statements — a prepared statement named _pg3_0 by one caller is still on the
# backend when the next caller prepares its own _pg3_0, and Postgres refuses the
# duplicate name (DuplicatePreparedStatement, Sentry PYTHON-FASTAPI-9). Local and
# session-mode connections (port 5432) never saw this because the connection is
# not shared. Do not remove without moving off the transaction pooler.
engine = create_engine(
    settings.sqlalchemy_database_url,
    echo=(settings.environment == "development"),
    hide_parameters=True,
    # 5+5 caps any one process at 10 connections. The session-mode pooler
    # (port 5432, used by local dev) allows 15 CLIENTS IN TOTAL across
    # everything, and Postgres itself allows 60 connections total on this
    # instance — so the old 10+30 let a single backend exhaust the whole
    # allowance and lock out the cron services (Supavisor EMAXCONNSESSION,
    # 2026-08-20). Production's transaction pooler (6543) hands connections
    # back between statements, so it does not need a large client-side pool.
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()
