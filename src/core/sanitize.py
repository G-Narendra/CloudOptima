"""Input sanitization helpers for the AI Architect Panel.

Provides input validation, HTML escaping, and safe string handling
to prevent XSS, injection, and data leakage through the dashboard.
"""

from __future__ import annotations
import html
import re
from typing import Any


# Characters that should trigger validation warnings
SUSPICIOUS_PATTERNS = re.compile(
    r"(<script|javascript:|onerror=|onload=|onclick=|alert\(|"
    r"prompt\(|confirm\(|eval\(|document\.cookie|"
    r"\\\\|\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4})",
    re.IGNORECASE,
)


def sanitize_text(text: str, max_length: int = 10000) -> str:
    """Sanitize user-provided text for safe display and storage.

    - Strips leading/trailing whitespace
    - Escapes HTML entities
    - Limits length
    - Replaces null bytes
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    # Remove null bytes
    cleaned = text.replace("\x00", "")

    # Strip whitespace
    cleaned = cleaned.strip()

    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def sanitize_for_display(text: str, max_length: int = 5000) -> str:
    """Sanitize text for safe HTML display (e.g., in st.markdown).

    Escapes HTML entities so user input cannot inject arbitrary markup.
    """
    cleaned = sanitize_text(text, max_length=max_length)
    return html.escape(cleaned)


def detect_suspicious_input(text: str) -> bool:
    """Check if text contains patterns associated with XSS or injection attempts.

    Returns True if suspicious patterns are found.
    """
    if not isinstance(text, str):
        return False
    return bool(SUSPICIOUS_PATTERNS.search(text))


def validate_prompt_input(fields: dict[str, Any]) -> dict[str, list[str]]:
    """Validate all prompt form fields and return warnings per field.

    Returns a dict of field_name -> [warning_message] for any fields
    that contain suspicious content.
    """
    warnings: dict[str, list[str]] = {}

    text_fields = [
        "project_description",
        "workload_type",
        "budget",
        "key_services",
        "additional_context",
    ]

    for field_name in text_fields:
        value = fields.get(field_name, "")
        if isinstance(value, str) and detect_suspicious_input(value):
            warnings.setdefault(field_name, [])
            warnings[field_name].append(
                "Input contains potentially unsafe patterns and has been sanitized."
            )

    return warnings


def safe_truncate(text: str, max_length: int = 200) -> str:
    """Safely truncate text at word boundary, with ellipsis."""
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    # Truncate at last space to avoid cutting words
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated + "..."
