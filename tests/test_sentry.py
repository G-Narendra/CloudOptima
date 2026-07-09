"""Tests for Sentry error tracking integration."""

from unittest.mock import patch, MagicMock

from src.core.sentry import (
    init_sentry,
    capture_error,
    set_user_context,
    add_breadcrumb,
    is_initialized,
    reset_sentry,
)


class TestSentryInit:
    """Test Sentry initialization behavior."""

    def teardown_method(self):
        reset_sentry()

    def test_init_skipped_when_no_dsn(self):
        """Should skip initialization when no DSN is configured."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = ""
            mock_settings.demo_mode = True

            result = init_sentry()
            assert result is False
            assert is_initialized() is False

    def test_init_with_dsn(self):
        """Should initialize Sentry when DSN is provided."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"
            mock_settings.demo_mode = False
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init") as mock_init:
                result = init_sentry()
                assert result is True
                assert is_initialized() is True
                mock_init.assert_called_once()
                args, kwargs = mock_init.call_args
                assert kwargs["dsn"] == "https://key@sentry.io/project"
                assert kwargs["environment"] == "production"
                assert "ai-architect-panel" in kwargs["release"]

    def test_init_idempotent(self):
        """Calling init_sentry multiple times should only init once."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"
            mock_settings.demo_mode = False
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init") as mock_init:
                init_sentry()
                init_sentry()
                init_sentry()
                # Should only have been called once
                assert mock_init.call_count == 1

    def test_init_demo_environment(self):
        """Should use 'demo' environment when DEMO_MODE is true."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"
            mock_settings.demo_mode = True
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init") as mock_init:
                init_sentry()
                args, kwargs = mock_init.call_args
                assert kwargs["environment"] == "demo"

    def test_init_production_environment(self):
        """Should use 'production' environment when DEMO_MODE is false."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"
            mock_settings.demo_mode = False
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init") as mock_init:
                init_sentry()
                args, kwargs = mock_init.call_args
                assert kwargs["environment"] == "production"

    def test_init_custom_dsn_overrides_settings(self):
        """Should use explicitly provided DSN over settings."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://default@sentry.io/project"
            mock_settings.demo_mode = False
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init") as mock_init:
                init_sentry(dsn="https://custom@sentry.io/project")
                args, kwargs = mock_init.call_args
                assert kwargs["dsn"] == "https://custom@sentry.io/project"

    def test_init_custom_environment(self):
        """Should use explicitly provided environment."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init") as mock_init:
                init_sentry(environment="staging")
                args, kwargs = mock_init.call_args
                assert kwargs["environment"] == "staging"

    def test_init_sdk_failure_graceful(self):
        """Should handle sentry_sdk import/init failures gracefully."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"

            with patch("sentry_sdk.init", side_effect=Exception("SDK error")):
                result = init_sentry()
                assert result is False


class TestCaptureError:
    """Test manual error capture."""

    def teardown_method(self):
        reset_sentry()

    def test_capture_error_safe_without_init(self):
        """Should not crash when Sentry is not initialized."""
        error = ValueError("test error")
        result = capture_error(error)
        assert result is None

    def test_capture_error_with_context(self):
        """Should pass context to Sentry."""
        with patch("sentry_sdk.push_scope") as mock_push_scope:
            mock_scope = MagicMock()
            mock_push_scope.return_value.__enter__.return_value = mock_scope
            mock_scope.set_extra = MagicMock()
            mock_scope.__enter__.return_value.set_extra = MagicMock()

            with patch("sentry_sdk.capture_exception") as mock_capture:
                mock_capture.return_value = "event_123"

                error = ValueError("test")
                result = capture_error(error, context={"session_id": "session_abc"})
                assert result == "event_123"


class TestUserContext:
    """Test user context setting."""

    def teardown_method(self):
        reset_sentry()

    def test_set_user_context(self):
        """Should set user context for Sentry."""
        with patch("sentry_sdk.set_user") as mock_set_user:
            set_user_context("user_123", role="architect")
            mock_set_user.assert_called_once_with({"id": "user_123", "role": "architect"})


class TestBreadcrumbs:
    """Test breadcrumb addition."""

    def teardown_method(self):
        reset_sentry()

    def test_add_breadcrumb(self):
        """Should add breadcrumb to current transaction."""
        with patch("sentry_sdk.add_breadcrumb") as mock_add:
            add_breadcrumb("Agent started", category="agent", level="info", data={"agent": "architect"})
            mock_add.assert_called_once()
            _, kwargs = mock_add.call_args
            assert kwargs["message"] == "Agent started"
            assert kwargs["category"] == "agent"


class TestReset:
    """Test reset functionality."""

    def teardown_method(self):
        reset_sentry()

    def test_reset_sentry(self):
        """Verify reset allows re-initialization."""
        with patch("src.core.sentry.settings") as mock_settings:
            mock_settings.sentry_dsn = "https://key@sentry.io/project"
            mock_settings.demo_mode = False
            mock_settings.app_version = "1.0.0"

            with patch("sentry_sdk.init"):
                init_sentry()
                assert is_initialized() is True
                reset_sentry()
                assert is_initialized() is False


class TestBeforeSend:
    """Test the before_send data sanitization callback."""

    def teardown_method(self):
        reset_sentry()

    def test_before_send_removes_vars_from_stacktrace(self):
        """Should strip local variables from stack frames."""
        from src.core.sentry import _before_send

        event = {
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {"filename": "test.py", "vars": {"password": "secret123", "api_key": "sk-..."}},
                                {"filename": "other.py", "vars": {"data": "ok"}},
                            ]
                        }
                    }
                ]
            }
        }

        result = _before_send(event)
        frames = result["exception"]["values"][0]["stacktrace"]["frames"]
        assert "vars" not in frames[0]
        assert "vars" not in frames[1]

    def test_before_send_redacts_auth_headers(self):
        """Should redact sensitive headers."""
        from src.core.sentry import _before_send

        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer token123",
                    "content-type": "application/json",
                    "x-api-key": "secret",
                },
                "data": {"sensitive": "data"},
                "cookies": "session=abc",
            }
        }

        result = _before_send(event)
        headers = result["request"]["headers"]
        assert headers["authorization"] == "[REDACTED]"
        assert headers["x-api-key"] == "[REDACTED]"
        assert headers["content-type"] == "application/json"  # not redacted
        assert "data" not in result["request"]
        assert "cookies" not in result["request"]
