"""The AI Architect Panel — Sentry Error Tracking

Initializes Sentry SDK for production error monitoring with:
- Performance tracing (auto-instrumentation of functions)
- Session tracking for user context
- Error grouping and fingerprinting
- Environment-aware configuration
- Comprehensive data sanitization (stack vars, headers, cookies, query params)

Usage:
    from src.core.sentry import init_sentry, capture_error

    init_sentry()         # Called once at app startup
    capture_error(e)      # Manually capture exceptions
"""

from __future__ import annotations
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs

from src.config import settings

logger = logging.getLogger(__name__)

# Sentinel to track whether Sentry has been initialized
_sentry_initialized = False

# Query parameter keys known to contain sensitive data that should be redacted
SENSITIVE_QUERY_PARAMS = frozenset({
    "api_key", "apikey", "api-key",
    "token", "access_token", "auth_token",
    "secret", "secret_key", "client_secret",
    "password", "passwd", "pwd",
    "key", "key_id",
    "session", "session_id",
    "code", "authorization_code",
    "refresh_token",
    "signature",
    "private_key",
})


def _redact_query_params(url: str) -> str:
    """Redact sensitive query parameters from a URL.

    Removes the values of known sensitive params while preserving the keys
    so developers can see WHICH param was redacted.
    """
    if "?" not in url:
        return url

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        redacted = False

        for key in list(params.keys()):
            if key.lower() in SENSITIVE_QUERY_PARAMS:
                params[key] = ["[REDACTED]"]
                redacted = True

        if not redacted:
            return url

        # Reconstruct URL with redacted params
        new_query = "&".join(
            f"{k}={v[0]}" if len(v) == 1
            else "&".join(f"{k}={item}" for item in v)
            for k, v in params.items()
        )
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

    except Exception:
        # If parsing fails, return URL as-is
        return url


def init_sentry(dsn: Optional[str] = None, environment: Optional[str] = None) -> bool:
    """Initialize Sentry SDK for error tracking and performance monitoring.

    Returns True if Sentry was initialized, False if skipped (no DSN or
    already initialized). Safe to call multiple times — only initializes once.

    Args:
        dsn: Sentry DSN. Defaults to settings.sentry_dsn.
        environment: Deployment environment (e.g. "production", "staging").
                     Defaults to "production" if DEMO_MODE=false, "demo" otherwise.
    """
    global _sentry_initialized

    if _sentry_initialized:
        logger.debug("Sentry already initialized — skipping (idempotent)")
        return False

    resolved_dsn = dsn or settings.sentry_dsn
    if not resolved_dsn:
        logger.info("Sentry DSN not configured — skipping Sentry initialization")
        return False

    resolved_env = environment or ("production" if not settings.demo_mode else "demo")

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=resolved_dsn,
            environment=resolved_env,
            release=f"ai-architect-panel@{settings.app_version}",
            traces_sample_rate=0.25,  # Sample 25% of transactions for perf monitoring
            profiles_sample_rate=0.1,  # Sample 10% for profiling
            send_default_pii=False,  # Don't send user PII by default
            max_breadcrumbs=50,
            attach_stacktrace=True,
            # Ignore common non-actionable errors
            ignore_errors=[
                KeyboardInterrupt,
                SystemExit,
            ],
            # Before-send callback to filter sensitive data
            before_send=lambda event, hint: _before_send(event),
        )

        _sentry_initialized = True
        logger.info(f"Sentry initialized (env={resolved_env}, traces_sample_rate=0.25)")
        return True

    except Exception as e:
        logger.warning(f"Failed to initialize Sentry: {e}")
        return False


def _before_send(event: dict) -> Optional[dict]:
    """Filter sensitive data from Sentry events before sending.

    Sanitizes:
    - Stack frame local variables (removes vars entirely)
    - Request body and cookies
    - Authorization headers (authorization, cookie, x-api-key)
    - URL query parameters (api_key, token, secret, password, etc.)
    - Request URL (redacted version)
    """
    # Remove local variables from stacktraces to avoid leaking secrets
    for exception in event.get("exception", {}).get("values", []):
        for frame in exception.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)

    # Remove request body and cookies if present
    request = event.get("request", {})
    request.pop("data", None)
    request.pop("cookies", None)

    # Redact sensitive headers
    if "headers" in request:
        headers = request["headers"]
        sensitive_header_keys = {"authorization", "cookie", "x-api-key", "x-api-key"}
        for key in list(headers.keys()):
            if key.lower() in sensitive_header_keys:
                headers[key] = "[REDACTED]"

    # Redact query params in the request URL
    url = request.get("url", "")
    if url:
        request["url"] = _redact_query_params(url)

    return event


def capture_error(error: Exception, context: Optional[dict] = None) -> Optional[str]:
    """Manually capture an exception to Sentry with optional context.

    Safe to call even if Sentry is not initialized — returns None.
    Returns the Sentry event ID on success.
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)

            event_id = sentry_sdk.capture_exception(error)
            logger.debug(f"Captured error in Sentry: event_id={event_id}")
            return event_id

    except Exception as e:
        logger.debug(f"Failed to capture error in Sentry: {e}")
        return None


def set_user_context(user_id: str, **kwargs):
    """Set user context for Sentry events.

    Call this after authentication to associate errors with specific users.
    """
    try:
        import sentry_sdk

        sentry_sdk.set_user({"id": user_id, **kwargs})
    except Exception as e:
        logger.debug(f"Failed to set Sentry user context: {e}")


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: Optional[dict] = None):
    """Add a breadcrumb to the current Sentry transaction.

    Breadcrumbs create a trail of events leading up to an error.
    Safe to call even if Sentry is not initialized.
    """
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except Exception as e:
        logger.debug(f"Failed to add Sentry breadcrumb: {e}")


def is_initialized() -> bool:
    """Check whether Sentry has been initialized."""
    return _sentry_initialized


def reset_sentry():
    """Reset Sentry initialization state (useful for testing)."""
    global _sentry_initialized
    _sentry_initialized = False
