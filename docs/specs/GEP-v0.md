# GEP v0 — Geneclaw Evolution Protocol Specification

**Status:** Implemented (v0.1.0)
**Author:** Clawland-AI Engineering
**Date:** 2026-02-18

---

## 1. Overview

GEP v0 implements a closed-loop self-improvement protocol for the nanobot AI agent framework. The protocol follows the lifecycle:

```
Observe → Diagnose → Propose → Gate → Execute → Evaluate → Record
```

By default, the protocol runs in **dry-run mode** — proposals are generated but never applied without explicit human approval (`--apply` flag).

## 2. Architecture

```
geneclaw/
├── __init__.py       # Package metadata
├── models.py         # Pydantic models (RunEvent, EvolutionProposal)
├── redact.py         # Secret redaction utilities
├── recorder.py       # JSONL event recorder (observability)
├── evolver.py        # Heuristic + LLM-assisted proposal generator
├── gatekeeper.py     # Safety validation before apply
├── apply.py          # Unified diff application with rollback
└── cli.py            # Typer CLI: nanobot geneclaw {status,evolve,apply}
```

## 3. Data Models

### 3.1 RunEvent

Recorded to `<workspace>/geneclaw/runs/<session_key>/YYYYMMDD.jsonl`

| Field | Type | Description |
|-------|------|-------------|
| timestamp | string (ISO 8601) | UTC timestamp |
| session_key | string | Session identifier |
| event_type | enum | `inbound_msg`, `tool_start`, `tool_end`, `exception`, `outbound_msg` |
| channel | string? | Source channel |
| tool_name | string? | Tool name for tool events |
| duration_ms | float? | Duration for tool_end events |
| success | bool? | Success status |
| error | string? | Error message (redacted) |
| preview | string? | Message preview (clipped + redacted) |

### 3.2 EvolutionProposal

```json
{
  "id": "uuid4",
  "title": "short title",
  "objective": "what this achieves",
  "evidence": ["evidence line 1", "..."],
  "risk_level": "low | medium | high",
  "files_touched": ["relative/file/path"],
  "unified_diff": "valid unified diff",
  "tests_to_run": ["pytest tests/..."],
  "rollback_plan": "how to undo"
}
```

## 4. Configuration

Added to `nanobot/config/schema.py` as `GeneclawConfig`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| enabled | bool | false | Enable geneclaw observability + evolution |
| log_max_chars | int | 500 | Max chars per event preview |
| redact_enabled | bool | true | Redact secrets in logs |
| allow_apply_default | bool | false | Must be true to allow --apply |
| allowlist_paths | list[str] | geneclaw/, nanobot/, tests/, docs/ | Allowed file paths in proposals |
| denylist_paths | list[str] | .env, secrets/, .git/, config.json | Blocked file paths |
| max_patch_lines | int | 500 | Maximum diff lines allowed |

## 5. Safety Gates

### 5.1 Gatekeeper Checks
1. **Path allowlist** — all `files_touched` must start with an allowed prefix
2. **Path denylist** — no `files_touched` may match a denied path
3. **Diff size** — `unified_diff` line count ≤ `max_patch_lines`
4. **Secret scan** — diff is scanned for API keys, tokens, PEM keys
5. **Suspicious patterns** — `eval()`, `exec()`, `os.system()`, `subprocess.call()`

### 5.2 Apply Safety
- Default mode is **dry-run** (validate only, no file changes)
- Apply requires `--apply` CLI flag AND `allow_apply_default=true` in config
- On apply: creates git branch `evo/<timestamp>-<slug>`, applies patch, runs pytest
- On test failure: automatic rollback (delete branch, restore previous state)

## 6. CLI Commands

```bash
# Show status
nanobot geneclaw status

# Generate a proposal (dry-run by default)
nanobot geneclaw evolve --since 24 --max-events 500

# Generate and apply
nanobot geneclaw evolve --apply

# Apply a saved proposal file
nanobot geneclaw apply proposal.json --apply
```

## 7. Integration Points

### 7.1 Agent Loop (nanobot/agent/loop.py)
When `geneclaw.enabled=true`:
- `_process_message()`: records inbound messages, outbound responses, exceptions
- `_run_agent_loop()`: records tool start/end with duration and success/failure

### 7.2 Recommendations
- Set `tools.restrictToWorkspace=true` for geneclaw workflows
- Review proposals before applying (dry-run first)
- Monitor `<workspace>/geneclaw/runs/` for observability data

## 8. Failure Handling

| Scenario | Behaviour |
|----------|-----------|
| LLM returns invalid JSON | `json_repair` attempts fix; falls back to no-op proposal |
| LLM returns empty | No-op proposal with diagnosis summary |
| Gatekeeper rejects | Proposal saved but not applied; reasons reported |
| Patch fails `git apply --check` | No files modified; error reported |
| Tests fail after apply | Automatic rollback; branch deleted |
| Git unavailable | Patch skipped; error reported |

## 9. Rollback Strategy

- **Before apply:** no changes made; delete proposal JSON if unwanted
- **After apply (git):** `git checkout -` to return to previous branch, `git branch -D evo/<branch>` to delete
- **After apply (no git):** manual file restore from backup

## 10. Recommended Allowlist Strategy

### Principle: Minimal Surface, Incremental Trust

Start with the **smallest possible allowlist** and expand only after successful,
audited evolution cycles.

### Phase 1 — Bootstrap (recommended starting point)

```json
{
  "allowlist_paths": ["geneclaw/", "docs/"],
  "denylist_paths": [".env", "secrets/", ".git/", "config.json", "pyproject.toml"]
}
```

**Rationale**: The evolver can only modify its own code (`geneclaw/`) and
documentation (`docs/`). This prevents accidental changes to the core nanobot
framework, CI/CD configs, or dependency manifests during the initial trust-building
phase.

### Phase 2 — Expanded (after ≥5 successful, reviewed proposals)

```json
{
  "allowlist_paths": ["geneclaw/", "docs/", "tests/"],
  "denylist_paths": [".env", "secrets/", ".git/", "config.json", "pyproject.toml"]
}
```

Adding `tests/` lets the evolver propose test improvements and new test cases
alongside code fixes.

### Phase 3 — Full development scope (after ≥20 reviewed proposals)

```json
{
  "allowlist_paths": ["geneclaw/", "nanobot/", "tests/", "docs/"],
  "denylist_paths": [".env", "secrets/", ".git/", "config.json", "pyproject.toml",
                     ".github/", "nanobot/cli/"]
}
```

Allows modifications to the nanobot framework itself, but still denies CI/CD
workflows and the CLI entry point (which controls security-critical dispatch).

### Hard Denylist (never allow)

These paths must remain on the denylist at all phases:

| Path | Reason |
|------|--------|
| `.env` | Contains secrets |
| `secrets/` | Contains secrets |
| `.git/` | Repository internals |
| `config.json` | Runtime configuration with API keys |
| `.github/workflows/` | CI/CD pipeline (supply-chain risk) |

### Governance Checklist

Before expanding the allowlist:

1. Review the `nanobot geneclaw report` output — success rate should be ≥ 80%
2. Confirm all prior proposals were human-reviewed (check `docs/devlog/`)
3. Run `nanobot geneclaw doctor` and resolve any warnings
4. Update this section with the date and rationale for the expansion
