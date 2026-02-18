"""Secret redaction utilities for GEP v0."""

from __future__ import annotations

import re

# Patterns that match common secret formats.
# Each tuple: (compiled regex, replacement label).
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Generic API keys / tokens in key=value or key: value (including JSON-escaped quotes)
    (
        re.compile(
            r"""(?i)(api[_-]?key|api[_-]?secret|token|secret|password|passwd|authorization|bearer)"""
            r"""(\s*[:=]\s*)(\\?['"]?)([A-Za-z0-9_\-/+=.]{8,})(\3)""",
        ),
        r"\1\2\3[REDACTED]\5",
    ),
    # Bearer tokens in headers
    (
        re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-/+=.]{8,})"),
        r"\1[REDACTED]",
    ),
    # AWS-style keys (AKIA...)
    (
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "[REDACTED_AWS_KEY]",
    ),
    # GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_)
    (
        re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,})\b"),
        "[REDACTED_GH_TOKEN]",
    ),
    # Slack tokens (xoxb-, xoxp-, xoxs-, xapp-)
    (
        re.compile(r"\b(xox[bpsa]-[A-Za-z0-9\-]{10,})\b"),
        "[REDACTED_SLACK_TOKEN]",
    ),
    # Generic long hex strings (32+ chars) that look like secrets
    (
        re.compile(r"\b([0-9a-fA-F]{32,})\b"),
        "[REDACTED_HEX]",
    ),
    # PEM private keys
    (
        re.compile(
            r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----.*?-----END\s+(RSA\s+)?PRIVATE\s+KEY-----",
            re.DOTALL,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


def redact_secrets(text: str) -> str:
    """Replace likely secrets in *text* with redaction placeholders.

    This is a best-effort heuristic scanner.  It is intentionally aggressive
    to avoid leaking credentials into run logs.
    """
    result = text
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result
