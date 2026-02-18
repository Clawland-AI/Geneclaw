"""Tests for geneclaw doctor checks (M4.1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from geneclaw.doctor import CheckResult, run_checks, get_next_steps


def _make_config(
    *,
    enabled: bool = True,
    allow_apply: bool = False,
    restrict_workspace: bool = True,
    allowlist: list[str] | None = None,
    denylist: list[str] | None = None,
    redact: bool = True,
) -> MagicMock:
    """Build a minimal mock Config for doctor tests."""
    gc = MagicMock()
    gc.enabled = enabled
    gc.allow_apply_default = allow_apply
    gc.allowlist_paths = allowlist if allowlist is not None else ["nanobot/", "geneclaw/"]
    gc.denylist_paths = denylist if denylist is not None else [".env", ".git/"]
    gc.redact_enabled = redact

    tools = MagicMock()
    tools.restrict_to_workspace = restrict_workspace

    config = MagicMock()
    config.geneclaw = gc
    config.tools = tools
    return config


def test_doctor_checks_enabled(tmp_path: Path) -> None:
    """When geneclaw is enabled, the enabled check should pass."""
    config = _make_config(enabled=True)
    results = run_checks(tmp_path, config)
    enabled_check = next(r for r in results if r.name == "geneclaw.enabled")
    assert enabled_check.passed is True
    assert enabled_check.severity == "ok"


def test_doctor_checks_disabled(tmp_path: Path) -> None:
    """When geneclaw is disabled, the enabled check should fail with error."""
    config = _make_config(enabled=False)
    results = run_checks(tmp_path, config)
    enabled_check = next(r for r in results if r.name == "geneclaw.enabled")
    assert enabled_check.passed is False
    assert enabled_check.severity == "error"


def test_doctor_checks_restrict_workspace_on(tmp_path: Path) -> None:
    """When restrict_to_workspace is on, severity should be ok."""
    config = _make_config(restrict_workspace=True)
    results = run_checks(tmp_path, config)
    rtw = next(r for r in results if r.name == "restrict_to_workspace")
    assert rtw.severity == "ok"
    assert "ON" in rtw.message


def test_doctor_checks_restrict_workspace_off(tmp_path: Path) -> None:
    """When restrict_to_workspace is off, doctor should warn."""
    config = _make_config(restrict_workspace=False)
    results = run_checks(tmp_path, config)
    rtw = next(r for r in results if r.name == "restrict_to_workspace")
    assert rtw.severity == "warn"
    assert "OFF" in rtw.message


def test_doctor_warns_missing_runs_dir(tmp_path: Path) -> None:
    """When runs dir doesn't exist, doctor should note it will be auto-created."""
    config = _make_config()
    results = run_checks(tmp_path, config)
    runs_check = next(r for r in results if r.name == "runs_dir_writable")
    assert runs_check.passed is True
    assert "does not exist yet" in runs_check.message


def test_doctor_runs_dir_writable(tmp_path: Path) -> None:
    """When runs dir exists and is writable, check should pass."""
    runs_dir = tmp_path / "geneclaw" / "runs"
    runs_dir.mkdir(parents=True)
    config = _make_config()
    results = run_checks(tmp_path, config)
    runs_check = next(r for r in results if r.name == "runs_dir_writable")
    assert runs_check.passed is True
    assert "writable" in runs_check.message.lower()


def test_doctor_empty_denylist(tmp_path: Path) -> None:
    """Empty denylist should be flagged as error."""
    config = _make_config(denylist=[])
    results = run_checks(tmp_path, config)
    deny_check = next(r for r in results if r.name == "denylist_paths")
    assert deny_check.passed is False
    assert deny_check.severity == "error"


def test_doctor_empty_allowlist(tmp_path: Path) -> None:
    """Empty allowlist should be flagged as warn."""
    config = _make_config(allowlist=[])
    results = run_checks(tmp_path, config)
    allow_check = next(r for r in results if r.name == "allowlist_paths")
    assert allow_check.severity == "warn"


def test_doctor_dry_run_default_safe(tmp_path: Path) -> None:
    """When allow_apply_default=false, dry-run default should be ok."""
    config = _make_config(allow_apply=False)
    results = run_checks(tmp_path, config)
    dry_check = next(r for r in results if r.name == "dry_run_default")
    assert dry_check.passed is True
    assert dry_check.severity == "ok"


def test_doctor_allow_apply_warns(tmp_path: Path) -> None:
    """When allow_apply_default=true, doctor should warn."""
    config = _make_config(allow_apply=True)
    results = run_checks(tmp_path, config)
    dry_check = next(r for r in results if r.name == "dry_run_default")
    assert dry_check.severity == "warn"


def test_doctor_outputs_next_steps() -> None:
    """get_next_steps should return actionable commands."""
    config = _make_config(enabled=False)
    steps = get_next_steps(config)
    assert len(steps) >= 4
    # Should contain the enable hint when disabled
    assert any("enabled" in s.lower() for s in steps)
    # Should contain status command
    assert any("nanobot geneclaw status" in s for s in steps)
    # Should contain evolve command
    assert any("evolve" in s for s in steps)


def test_doctor_redact_disabled_warns(tmp_path: Path) -> None:
    """When redact is disabled, doctor should warn."""
    config = _make_config(redact=False)
    results = run_checks(tmp_path, config)
    redact_check = next(r for r in results if r.name == "redact_enabled")
    assert redact_check.severity == "warn"
