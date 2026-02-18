"""Apply — safely apply a unified diff behind the gatekeeper (GEP v0)."""

from __future__ import annotations

import subprocess
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from geneclaw.gatekeeper import validate_proposal
from geneclaw.models import EvolutionProposal


# ---------------------------------------------------------------------------
# Diff application
# ---------------------------------------------------------------------------


def apply_unified_diff(
    proposal: EvolutionProposal,
    repo_root: Path,
    *,
    allowlist_paths: list[str] | None = None,
    denylist_paths: list[str] | None = None,
    max_patch_lines: int = 500,
    dry_run: bool = True,
    run_tests: bool = True,
) -> tuple[bool, str]:
    """Validate and optionally apply a proposal's unified diff.

    Parameters
    ----------
    proposal:
        The evolution proposal containing the diff.
    repo_root:
        Absolute path to the repository root.
    allowlist_paths / denylist_paths / max_patch_lines:
        Passed to ``validate_proposal()``.
    dry_run:
        If True (default), only validate — do NOT modify files.
    run_tests:
        If True and not dry_run, run ``pytest -q`` after applying.

    Returns
    -------
    tuple[bool, str]
        ``(success, message)``
    """
    # 1. Gatekeeper validation
    ok, reasons = validate_proposal(
        proposal,
        allowlist_paths=allowlist_paths,
        denylist_paths=denylist_paths,
        max_patch_lines=max_patch_lines,
    )
    if not ok:
        return False, "Gatekeeper rejected proposal:\n" + "\n".join(f"  - {r}" for r in reasons)

    if dry_run:
        return True, "Dry-run: proposal passed gatekeeper validation. No files modified."

    # 2. Write diff to temp file
    diff_text = proposal.unified_diff
    if not diff_text.strip():
        return True, "Empty diff — nothing to apply."

    tmp_patch = Path(tempfile.mktemp(suffix=".patch"))
    try:
        tmp_patch.write_text(diff_text, encoding="utf-8")

        # 3. Check if git is available and repo is a git repo
        has_git = _has_git(repo_root)
        branch_name: str | None = None

        if has_git:
            # Create evo branch
            slug = proposal.title.lower().replace(" ", "-")[:30]
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            branch_name = f"evo/{ts}-{slug}"
            _run_git(repo_root, ["checkout", "-b", branch_name])

        # 4. Apply patch
        try:
            result = subprocess.run(
                ["git", "apply", "--check", str(tmp_patch)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                _rollback_branch(repo_root, branch_name, has_git)
                return False, f"Patch apply --check failed:\n{result.stderr}"

            subprocess.run(
                ["git", "apply", str(tmp_patch)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            _rollback_branch(repo_root, branch_name, has_git)
            return False, "git command not found — cannot apply patch."
        except subprocess.CalledProcessError as exc:
            _rollback_branch(repo_root, branch_name, has_git)
            return False, f"Patch apply failed:\n{exc.stderr}"

        # 5. Run tests
        test_passed = True
        test_output = ""
        if run_tests:
            try:
                test_result = subprocess.run(
                    ["pytest", "-q"],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                test_output = test_result.stdout + test_result.stderr
                test_passed = test_result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                test_output = str(exc)
                test_passed = False

        if not test_passed:
            _rollback_branch(repo_root, branch_name, has_git)
            return False, f"Tests failed after apply — rolled back.\n{test_output}"

        # 6. Commit on success
        if has_git:
            _run_git(repo_root, ["add", "-A"])
            commit_msg = (
                f"feat(geneclaw): {proposal.title}\n\n"
                f"Evo-Event-ID: {proposal.id}\n"
                f"Risk-Level: {proposal.risk_level}\n"
                f"Tests: pytest -q"
            )
            _run_git(repo_root, ["commit", "-m", commit_msg])

        return True, f"Proposal applied successfully on branch '{branch_name or 'HEAD'}'."

    finally:
        if tmp_patch.exists():
            tmp_patch.unlink()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _has_git(repo_root: Path) -> bool:
    """Check if repo_root is a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )


def _rollback_branch(
    repo_root: Path, branch_name: str | None, has_git: bool
) -> None:
    """Attempt to roll back to the previous branch."""
    if not has_git or not branch_name:
        return
    try:
        _run_git(repo_root, ["checkout", "-"])
        _run_git(repo_root, ["branch", "-D", branch_name])
        logger.info(f"Rolled back: deleted branch {branch_name}")
    except Exception as exc:
        logger.warning(f"Rollback failed: {exc}")
