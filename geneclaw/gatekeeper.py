"""Gatekeeper — validates evolution proposals before apply (GEP v0)."""

from __future__ import annotations

import re
from typing import Any

from geneclaw.models import EvolutionProposal
from geneclaw.redact import redact_secrets


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_proposal(
    proposal: EvolutionProposal,
    *,
    allowlist_paths: list[str] | None = None,
    denylist_paths: list[str] | None = None,
    max_patch_lines: int = 500,
) -> tuple[bool, list[str]]:
    """Validate an evolution proposal against safety constraints.

    Parameters
    ----------
    proposal:
        The proposal to validate.
    allowlist_paths:
        If non-empty, all ``files_touched`` must start with one of these prefixes.
    denylist_paths:
        Paths that must NOT appear in ``files_touched`` or in the diff.
    max_patch_lines:
        Maximum number of lines allowed in ``unified_diff``.

    Returns
    -------
    tuple[bool, list[str]]
        ``(ok, reasons)`` — ``ok`` is True if all checks pass.
    """
    reasons: list[str] = []
    allow = allowlist_paths or []
    deny = denylist_paths or []

    # --- Check files_touched against denylist ---
    for fp in proposal.files_touched:
        normalised = fp.replace("\\", "/")
        for dp in deny:
            dp_norm = dp.replace("\\", "/")
            if normalised.startswith(dp_norm) or normalised == dp_norm:
                reasons.append(f"File '{fp}' matches denylist entry '{dp}'")

    # --- Check files_touched against allowlist ---
    if allow:
        for fp in proposal.files_touched:
            normalised = fp.replace("\\", "/")
            if not any(normalised.startswith(a.replace("\\", "/")) for a in allow):
                reasons.append(
                    f"File '{fp}' not in allowlist ({', '.join(allow)})"
                )

    # --- Check diff line count ---
    diff_lines = proposal.unified_diff.splitlines()
    if len(diff_lines) > max_patch_lines:
        reasons.append(
            f"Diff has {len(diff_lines)} lines, exceeds max_patch_lines={max_patch_lines}"
        )

    # --- Scan diff for secrets ---
    redacted = redact_secrets(proposal.unified_diff)
    if redacted != proposal.unified_diff:
        reasons.append("Diff appears to contain secrets (redaction triggered)")

    # --- Scan for suspicious dependency additions ---
    _suspicious = _scan_suspicious_deps(proposal.unified_diff)
    reasons.extend(_suspicious)

    ok = len(reasons) == 0
    return ok, reasons


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"^\+.*subprocess\.call\(", re.MULTILINE),
        "Diff adds subprocess.call() — review for command injection",
    ),
    (
        re.compile(r"^\+.*os\.system\(", re.MULTILINE),
        "Diff adds os.system() — review for command injection",
    ),
    (
        re.compile(r"^\+.*eval\(", re.MULTILINE),
        "Diff adds eval() — review for code injection",
    ),
    (
        re.compile(r"^\+.*exec\(", re.MULTILINE),
        "Diff adds exec() — review for code injection",
    ),
]


def _scan_suspicious_deps(diff_text: str) -> list[str]:
    """Scan a unified diff for suspicious code patterns."""
    warnings: list[str] = []
    for pattern, msg in _SUSPICIOUS_PATTERNS:
        if pattern.search(diff_text):
            warnings.append(msg)
    return warnings
