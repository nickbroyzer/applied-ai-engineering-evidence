# `code/database/` — excerpts

Short passages from the private Zelbi repository, verbatim, each with its
source path and line range at Zelbi `4772472b` (`4772472bdf2f370ea3b54971d8e94c9474cf7aaf`). They are
the passages the write-ups and case studies cite. Full source files of the
core systems are no longer published here (show the work, not the recipe);
`MANIFEST.md` §6 lists what was removed. Where a write-up gives line numbers
at an older commit, it says which.

## Prepared statements off for the transaction pooler

`backend/app/database.py`, lines 1–30, at `4772472b`. Cited by: 04-troubleshooting/01-prepared-statements-vs-pooler.md.

```python
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

```

## Error reporting, off under pytest

`backend/app/observability.py`, lines 10–36, at `4772472b`. Cited by: 04-troubleshooting/01-prepared-statements-vs-pooler.md.

```python
def init_sentry(component: str) -> None:
    """Initialise Sentry if a DSN is configured. No-op when SENTRY_DSN is unset
    or when running under pytest, so local test runs never report."""
    global _enabled
    if "pytest" in sys.modules:
        return
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry_sdk not installed; error reporting disabled")
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=0.0,
        send_default_pii=False,
        # Log records become breadcrumbs, never events. Without this, every
        # logger.error and logger.exception in the codebase raises an issue,
        # including deliberately handled conditions.
        integrations=[LoggingIntegration(level=logging.INFO, event_level=None)],
    )
    sentry_sdk.set_tag("component", component)
    _enabled = True
```

## An explicit capture inside each except block

`backend/app/observability.py`, lines 39–48, at `4772472b`. Cited by: 04-troubleshooting/01-prepared-statements-vs-pooler.md.

```python
def capture_exception(exc: BaseException, **tags: str) -> None:
    """Report an exception that the caller has already handled and swallowed."""
    if not _enabled:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        for key, value in tags.items():
            scope.set_tag(key, value)
        sentry_sdk.capture_exception(exc)
```
