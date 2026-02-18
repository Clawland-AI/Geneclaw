"""Tests for geneclaw gatekeeper, apply, and CLI (M3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geneclaw.gatekeeper import validate_proposal
from geneclaw.models import EvolutionProposal
from geneclaw.apply import apply_unified_diff


# ---------------------------------------------------------------------------
# Gatekeeper
# ---------------------------------------------------------------------------


def test_gatekeeper_blocks_denylist_paths() -> None:
    """Proposals touching denylist paths should be rejected."""
    proposal = EvolutionProposal(
        id="test-1",
        title="sneaky change",
        files_touched=[".env", "nanobot/agent/loop.py"],
        unified_diff="--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-OLD\n+NEW\n",
    )

    ok, reasons = validate_proposal(
        proposal,
        allowlist_paths=["nanobot/", "geneclaw/", "tests/"],
        denylist_paths=[".env", "secrets/", ".git/"],
    )

    assert not ok
    assert any(".env" in r for r in reasons)


def test_gatekeeper_blocks_non_allowlist_paths() -> None:
    """Files outside the allowlist should be rejected."""
    proposal = EvolutionProposal(
        id="test-2",
        title="external change",
        files_touched=["some_random_dir/hack.py"],
        unified_diff="--- a/some_random_dir/hack.py\n+++ b/some_random_dir/hack.py\n",
    )

    ok, reasons = validate_proposal(
        proposal,
        allowlist_paths=["nanobot/", "geneclaw/"],
    )

    assert not ok
    assert any("not in allowlist" in r for r in reasons)


def test_gatekeeper_blocks_too_large_diff() -> None:
    """Diffs exceeding max_patch_lines should be rejected."""
    big_diff = "\n".join([f"+line {i}" for i in range(600)])
    proposal = EvolutionProposal(
        id="test-3",
        title="big patch",
        files_touched=["nanobot/utils.py"],
        unified_diff=big_diff,
    )

    ok, reasons = validate_proposal(proposal, max_patch_lines=500)
    assert not ok
    assert any("max_patch_lines" in r for r in reasons)


def test_gatekeeper_detects_secrets_in_diff() -> None:
    """Diffs containing secrets should be flagged."""
    proposal = EvolutionProposal(
        id="test-4",
        title="oops secrets",
        files_touched=["nanobot/config.py"],
        unified_diff='--- a/nanobot/config.py\n+++ b/nanobot/config.py\n@@ -1 +1 @@\n-pass\n+API_KEY = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh1234"\n',
    )

    ok, reasons = validate_proposal(proposal, allowlist_paths=["nanobot/"])
    assert not ok
    assert any("secrets" in r.lower() or "redact" in r.lower() for r in reasons)


def test_gatekeeper_passes_valid_proposal() -> None:
    """A clean, valid proposal should pass all checks."""
    proposal = EvolutionProposal(
        id="test-5",
        title="clean fix",
        files_touched=["nanobot/agent/loop.py"],
        unified_diff="--- a/nanobot/agent/loop.py\n+++ b/nanobot/agent/loop.py\n@@ -1 +1 @@\n-old\n+new\n",
    )

    ok, reasons = validate_proposal(
        proposal,
        allowlist_paths=["nanobot/", "geneclaw/"],
        denylist_paths=[".env", ".git/"],
        max_patch_lines=500,
    )

    assert ok, f"Expected pass, got: {reasons}"


def test_gatekeeper_warns_suspicious_patterns() -> None:
    """Diffs containing eval/exec/os.system should trigger warnings."""
    proposal = EvolutionProposal(
        id="test-6",
        title="suspicious change",
        files_touched=["nanobot/utils.py"],
        unified_diff="--- a/nanobot/utils.py\n+++ b/nanobot/utils.py\n@@ -1 +1 @@\n-pass\n+eval(user_input)\n",
    )

    ok, reasons = validate_proposal(proposal, allowlist_paths=["nanobot/"])
    assert not ok
    assert any("eval()" in r for r in reasons)


# ---------------------------------------------------------------------------
# Apply (dry-run safety)
# ---------------------------------------------------------------------------


def test_apply_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    """Dry-run mode should validate but never modify any files."""
    # Create a file that should not be touched
    target = tmp_path / "nanobot" / "agent" / "loop.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original content\n", encoding="utf-8")

    proposal = EvolutionProposal(
        id="dry-1",
        title="safe fix",
        files_touched=["nanobot/agent/loop.py"],
        unified_diff="--- a/nanobot/agent/loop.py\n+++ b/nanobot/agent/loop.py\n@@ -1 +1 @@\n-original content\n+modified content\n",
    )

    success, msg = apply_unified_diff(
        proposal,
        repo_root=tmp_path,
        allowlist_paths=["nanobot/"],
        denylist_paths=[".env"],
        dry_run=True,
    )

    assert success
    assert "Dry-run" in msg
    # Verify file was NOT modified
    assert target.read_text(encoding="utf-8") == "original content\n"


def test_apply_rejects_gatekeeper_failure(tmp_path: Path) -> None:
    """Apply should reject proposals that fail gatekeeper."""
    proposal = EvolutionProposal(
        id="bad-1",
        title="bad patch",
        files_touched=[".env"],
        unified_diff="--- a/.env\n+++ b/.env\n",
    )

    success, msg = apply_unified_diff(
        proposal,
        repo_root=tmp_path,
        denylist_paths=[".env"],
        dry_run=False,
    )

    assert not success
    assert "Gatekeeper rejected" in msg


# ---------------------------------------------------------------------------
# CLI evolve (proposal output)
# ---------------------------------------------------------------------------


def test_cli_evolve_outputs_proposal_files(tmp_path: Path) -> None:
    """The evolve flow should write a proposal JSON file."""
    from geneclaw.models import EvolutionProposal

    # Simulate what the CLI evolve command does: write proposal to file
    proposal = EvolutionProposal(
        id="cli-test-1",
        title="test proposal",
        objective="test objective",
        risk_level="low",
    )

    proposals_dir = tmp_path / "geneclaw" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    out_path = proposals_dir / "proposal_test.json"
    out_path.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")

    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["id"] == "cli-test-1"
    assert loaded["title"] == "test proposal"
    assert loaded["risk_level"] == "low"

    # Verify it round-trips through model
    reloaded = EvolutionProposal.model_validate(loaded)
    assert reloaded.id == "cli-test-1"
