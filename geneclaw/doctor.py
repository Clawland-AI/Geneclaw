"""Doctor — read-only health checks for geneclaw configuration (GEP v0).

All checks are pure functions that inspect state without modifying anything.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from nanobot.config.schema import Config


@dataclass
class CheckResult:
    """Result of a single doctor check."""

    name: str
    passed: bool
    message: str
    severity: Literal["ok", "warn", "error"] = "ok"


def run_checks(workspace: Path, config: "Config") -> list[CheckResult]:
    """Run all doctor checks and return structured results.

    This function is read-only — it never modifies configuration or files.
    """
    results: list[CheckResult] = []
    gc = config.geneclaw

    # 1) geneclaw.enabled
    if gc.enabled:
        results.append(CheckResult(
            name="geneclaw.enabled",
            passed=True,
            message="Geneclaw observability is enabled.",
            severity="ok",
        ))
    else:
        results.append(CheckResult(
            name="geneclaw.enabled",
            passed=False,
            message=(
                "Geneclaw is disabled. Set geneclaw.enabled=true in "
                "~/.nanobot/config.json to activate observability and evolution."
            ),
            severity="error",
        ))

    # 2) allow_apply_default should be false (dry-run by default)
    if not gc.allow_apply_default:
        results.append(CheckResult(
            name="dry_run_default",
            passed=True,
            message="Dry-run is the default (allow_apply_default=false). Safe.",
            severity="ok",
        ))
    else:
        results.append(CheckResult(
            name="dry_run_default",
            passed=True,
            message=(
                "allow_apply_default=true — proposals CAN be applied directly. "
                "Consider setting to false for safety unless you explicitly need auto-apply."
            ),
            severity="warn",
        ))

    # 3) tools.restrict_to_workspace
    if config.tools.restrict_to_workspace:
        results.append(CheckResult(
            name="restrict_to_workspace",
            passed=True,
            message="tools.restrictToWorkspace is ON. Recommended for geneclaw workflows.",
            severity="ok",
        ))
    else:
        results.append(CheckResult(
            name="restrict_to_workspace",
            passed=True,
            message=(
                "tools.restrictToWorkspace is OFF. Strongly recommended to enable "
                "for geneclaw workflows to prevent tools from accessing files outside workspace."
            ),
            severity="warn",
        ))

    # 4) geneclaw/runs directory writable
    runs_dir = workspace / "geneclaw" / "runs"
    if runs_dir.exists():
        try:
            test_file = runs_dir / ".doctor_write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            results.append(CheckResult(
                name="runs_dir_writable",
                passed=True,
                message=f"Runs directory writable: {runs_dir}",
                severity="ok",
            ))
        except OSError as exc:
            results.append(CheckResult(
                name="runs_dir_writable",
                passed=False,
                message=f"Runs directory NOT writable: {runs_dir} ({exc})",
                severity="error",
            ))
    else:
        results.append(CheckResult(
            name="runs_dir_writable",
            passed=True,
            message=(
                f"Runs directory does not exist yet: {runs_dir}. "
                "It will be created automatically on first recorded event."
            ),
            severity="ok",
        ))

    # 5) allowlist / denylist validation
    if gc.allowlist_paths:
        results.append(CheckResult(
            name="allowlist_paths",
            passed=True,
            message=f"Allowlist ({len(gc.allowlist_paths)} entries): {', '.join(gc.allowlist_paths)}",
            severity="ok",
        ))
    else:
        results.append(CheckResult(
            name="allowlist_paths",
            passed=True,
            message="Allowlist is empty — all paths are allowed. Consider restricting.",
            severity="warn",
        ))

    if gc.denylist_paths:
        results.append(CheckResult(
            name="denylist_paths",
            passed=True,
            message=f"Denylist ({len(gc.denylist_paths)} entries): {', '.join(gc.denylist_paths)}",
            severity="ok",
        ))
    else:
        results.append(CheckResult(
            name="denylist_paths",
            passed=False,
            message="Denylist is empty — no paths are blocked. This is unsafe. Add at least .env, .git/, secrets/.",
            severity="error",
        ))

    # 6) redact_enabled
    if gc.redact_enabled:
        results.append(CheckResult(
            name="redact_enabled",
            passed=True,
            message="Secret redaction is enabled for run logs.",
            severity="ok",
        ))
    else:
        results.append(CheckResult(
            name="redact_enabled",
            passed=False,
            message="Secret redaction is DISABLED. Strongly recommended to enable.",
            severity="warn",
        ))

    return results


def get_next_steps(config: "Config") -> list[str]:
    """Return a list of suggested next-step commands (copy-pasteable)."""
    gc = config.geneclaw
    steps: list[str] = []

    if not gc.enabled:
        steps.append(
            '# Enable geneclaw in config:\n'
            '# Edit ~/.nanobot/config.json → set "geneclaw": {"enabled": true}'
        )

    steps.append("# Check status:")
    steps.append("nanobot geneclaw status")

    steps.append("# Generate run logs (interact with agent once):")
    steps.append('nanobot agent -m "Hello, what can you do?"')

    steps.append("# Generate your first evolution proposal (dry-run):")
    steps.append("nanobot geneclaw evolve --dry-run")

    steps.append("# View the latest proposal:")
    if os.name == "nt":
        steps.append("dir /b %USERPROFILE%\\.nanobot\\workspace\\geneclaw\\proposals\\")
    else:
        steps.append("ls ~/.nanobot/workspace/geneclaw/proposals/")

    return steps
