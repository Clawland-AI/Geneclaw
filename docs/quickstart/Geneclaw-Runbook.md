# Geneclaw Runbook — Getting Started with GEP v0

**Repository:** Clawland-AI/Geneclaw (upstream: HKUDS/nanobot)

This runbook gets you from zero to your first evolution proposal using only
CLI commands. No source code reading required.

---

## 1. Prerequisites

- Python >= 3.11
- Git installed
- nanobot + geneclaw installed:

```bash
# Clone and install
git clone https://github.com/Clawland-AI/Geneclaw.git
cd Geneclaw
pip install -e ".[dev]"

# Initial nanobot setup (creates ~/.nanobot/config.json + workspace)
nanobot onboard
```

## 2. Enable Geneclaw

Edit `~/.nanobot/config.json` and add/update the `geneclaw` section:

```json
{
  "geneclaw": {
    "enabled": true,
    "redactEnabled": true,
    "allowApplyDefault": false,
    "logMaxChars": 500,
    "maxPatchLines": 500,
    "allowlistPaths": ["geneclaw/", "nanobot/", "tests/", "docs/"],
    "denylistPaths": [".env", "secrets/", ".git/", "config.json"]
  },
  "tools": {
    "restrictToWorkspace": true
  }
}
```

Key settings:
- `enabled: true` — activates run event recording in the agent loop
- `allowApplyDefault: false` — ensures dry-run is the default (safe)
- `restrictToWorkspace: true` — recommended for geneclaw workflows

## 3. Run Doctor Check

Verify your setup is healthy:

```bash
nanobot geneclaw doctor
```

Expected output:
```
Geneclaw Doctor

  ✓ geneclaw.enabled: Geneclaw observability is enabled.
  ✓ dry_run_default: Dry-run is the default (allow_apply_default=false). Safe.
  ✓ restrict_to_workspace: tools.restrictToWorkspace is ON. Recommended.
  ✓ runs_dir_writable: Runs directory does not exist yet. Will be auto-created.
  ✓ allowlist_paths: Allowlist (4 entries): geneclaw/, nanobot/, tests/, docs/
  ✓ denylist_paths: Denylist (4 entries): .env, secrets/, .git/, config.json
  ✓ redact_enabled: Secret redaction is enabled for run logs.

  Summary: 7 ok, 0 warnings, 0 errors

Suggested next steps:
  ...
```

Fix any errors before proceeding.

## 4. Generate Run Logs

Interact with the agent to generate your first run events:

```bash
# Single message
nanobot agent -m "Hello, what tools do you have?"

# Or interactive mode
nanobot agent
```

Each interaction records events to:
```
~/.nanobot/workspace/geneclaw/runs/<session_key>/YYYYMMDD.jsonl
```

## 5. Check Status

```bash
nanobot geneclaw status
```

Shows: enabled state, session count, last run log timestamp.

## 6. Generate Your First Proposal

```bash
nanobot geneclaw evolve --dry-run
```

This will:
1. Load recent run events from all sessions
2. Run heuristic diagnosis (tool failures, exception clusters)
3. Call the LLM to generate an evolution proposal
4. Write the proposal JSON to `~/.nanobot/workspace/geneclaw/proposals/`
5. Display a summary (title, risk, files, diff stats)

The `--dry-run` flag (default) means **no files are modified**.

## 7. View & Understand the Proposal

```bash
# List proposals
ls ~/.nanobot/workspace/geneclaw/proposals/
# Windows: dir %USERPROFILE%\.nanobot\workspace\geneclaw\proposals\

# Read a proposal
cat ~/.nanobot/workspace/geneclaw/proposals/proposal_YYYYMMDD_HHMMSS.json
# Windows: type %USERPROFILE%\.nanobot\workspace\geneclaw\proposals\proposal_...json
```

Proposal structure:
```json
{
  "id": "uuid",
  "title": "short description",
  "objective": "what this evolution achieves",
  "evidence": ["diagnostic evidence..."],
  "risk_level": "low",
  "files_touched": ["nanobot/config/schema.py"],
  "unified_diff": "--- a/file\n+++ b/file\n...",
  "tests_to_run": ["pytest tests/..."],
  "rollback_plan": "how to undo"
}
```

## 8. Inspect Run Logs

JSONL files contain one event per line:

```bash
# View recent events
cat ~/.nanobot/workspace/geneclaw/runs/cli_direct/YYYYMMDD.jsonl

# Count events by type (Linux/Mac)
jq -r '.event_type' ~/.nanobot/workspace/geneclaw/runs/*/YYYYMMDD.jsonl | sort | uniq -c

# Find failures
jq 'select(.success == false)' ~/.nanobot/workspace/geneclaw/runs/*/YYYYMMDD.jsonl
```

Event types:
- `inbound_msg` — user message received
- `tool_start` / `tool_end` — tool call with duration and success
- `exception` — unhandled error
- `outbound_msg` — agent response sent

## 9. View Evolution Report

```bash
nanobot geneclaw report --since 48
```

Shows: evolve count, apply count, success rate, top failures, risk distribution.

## 10. Security Notes

1. **Dry-run by default**: The `--apply` flag is required to modify files. Even then,
   `allow_apply_default` must be `true` in config.

2. **Secret redaction**: All run logs are automatically scrubbed for API keys, tokens,
   PEM keys, and hex strings before writing to disk.

3. **Allowlist/Denylist**: Proposals can only touch files matching the allowlist and
   are blocked from touching denylist paths (`.env`, `.git/`, `secrets/`).

4. **Diff scanning**: Before apply, diffs are scanned for embedded secrets and
   suspicious patterns (`eval()`, `exec()`, `os.system()`).

5. **Auto-rollback**: If tests fail after applying a patch, the change is automatically
   rolled back (branch deleted, files restored).

6. **Workspace restriction**: Enable `tools.restrictToWorkspace=true` to prevent
   agent tools from accessing files outside the workspace.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `nanobot geneclaw doctor` | Health check (read-only) |
| `nanobot geneclaw status` | Show enabled state, runs, last log |
| `nanobot geneclaw evolve --dry-run` | Generate proposal without applying |
| `nanobot geneclaw evolve --apply` | Generate and apply (requires config) |
| `nanobot geneclaw apply <file> --dry-run` | Validate a saved proposal |
| `nanobot geneclaw apply <file> --apply` | Apply a saved proposal |
| `nanobot geneclaw report` | Show evolution stats (last 24h) |
