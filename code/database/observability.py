import logging
import os
import sys

logger = logging.getLogger(__name__)

_enabled = False


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


def capture_exception(exc: BaseException, **tags: str) -> None:
    """Report an exception that the caller has already handled and swallowed."""
    if not _enabled:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        for key, value in tags.items():
            scope.set_tag(key, value)
        sentry_sdk.capture_exception(exc)


def flush_sentry(timeout: float = 5.0) -> None:
    """Drain the send queue before a short-lived process exits."""
    if not _enabled:
        return
    import sentry_sdk

    sentry_sdk.flush(timeout=timeout)
