<div align="center">
  <h1>Geneclaw — Self-Evolving AI Agent Framework</h1>
  <p>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/GEP-v0.1.0-orange" alt="GEP Version">
    <img src="https://img.shields.io/badge/upstream-HKUDS%2Fnanobot-lightgrey" alt="Upstream">
  </p>
  <p><em>Built on <a href="https://github.com/HKUDS/nanobot">nanobot</a> — adds closed-loop self-improvement via the Geneclaw Evolution Protocol (GEP)</em></p>
</div>

---

**Geneclaw** extends the ultra-lightweight [nanobot](https://github.com/HKUDS/nanobot) AI agent with a **self-evolution engine** — enabling the agent to observe its own failures, diagnose root causes, propose constrained fixes, and safely apply them behind a multi-layered gatekeeper.

**Everything is dry-run by default. Nothing is applied without explicit human approval.**

## Key Capabilities

| Capability | Description |
|-----------|-------------|
| **Observability** | JSONL event recording for every agent interaction (inbound, tools, errors, outbound) |
| **Diagnosis** | Heuristic failure analysis + optional LLM-assisted root cause identification |
| **Evolution Proposals** | Structured JSON proposals with unified diffs, risk levels, and rollback plans |
| **Gatekeeper** | 5-layer safety validation (allowlist, denylist, diff size, secret scan, code pattern detection) |
| **Safe Apply** | Git-branched patch application with automated test execution and rollback on failure |
| **Autopilot** | Configurable multi-cycle evolution loop with risk-based auto-approve |
| **Benchmarks** | Pipeline performance measurement with synthetic workloads |
| **Event Store** | Append-only evolution lifecycle logging with secret redaction |
| **Reporting** | Aggregated pipeline statistics (table + JSON output) |
| **Doctor** | Read-only health checks with actionable suggestions |

## Architecture

```
                     Geneclaw Evolution Protocol (GEP v0)
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │   Observe ──→ Diagnose ──→ Propose ──→ Gate ──→ Apply      │
    │      │            │            │          │         │       │
    │   recorder    evolver      evolver    gatekeeper  apply     │
    │   (JSONL)    (heuristic    (JSON +    (5 checks)  (git +   │
    │               + LLM)       diff)                  pytest)  │
    │      │            │            │          │         │       │
    │      └────────────┴────────────┴──────────┴─────────┘       │
    │                         │                                   │
    │                    event_store                               │
    │                    (audit log)                               │
    │                                                             │
    ├─── autopilot (multi-cycle controller)                       │
    ├─── benchmarks (performance measurement)                     │
    ├─── doctor (health checks)                                   │
    └─── report (statistics aggregation)                          │
                                                                  │
    ┌─────────────────────────────────────────────────────────────┐
    │                  nanobot (upstream)                          │
    │   agent/loop.py ←→ channels ←→ providers ←→ tools           │
    └─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Clawland-AI/Geneclaw
├── geneclaw/                  # GEP v0 evolution engine
│   ├── __init__.py            # Package metadata (v0.1.0)
│   ├── models.py              # RunEvent, EvolutionProposal, EvoEvent
│   ├── redact.py              # Secret redaction (regex-based)
│   ├── recorder.py            # JSONL run event recorder
│   ├── evolver.py             # Heuristic + LLM proposal generator
│   ├── gatekeeper.py          # Safety validation (5 checks)
│   ├── apply.py               # Git-branched diff application
│   ├── event_store.py         # Append-only evolution event log
│   ├── report.py              # Statistics aggregation
│   ├── doctor.py              # Health checks
│   ├── autopilot.py           # Multi-cycle evolution controller
│   ├── benchmarks.py          # Pipeline performance benchmarks
│   └── cli.py                 # Typer CLI subcommands
├── nanobot/                   # Upstream agent framework (HKUDS/nanobot)
│   ├── agent/                 # Core agent loop + tools
│   ├── channels/              # Chat platform integrations
│   ├── providers/             # LLM providers
│   ├── config/                # Configuration schema
│   └── cli/                   # Main CLI entry point
├── tests/
│   ├── test_geneclaw_recorder.py
│   ├── test_geneclaw_evolver.py
│   ├── test_geneclaw_gatekeeper.py
│   ├── test_geneclaw_doctor.py
│   ├── test_geneclaw_events.py
│   └── test_geneclaw_autopilot.py
├── docs/
│   ├── specs/GEP-v0.md        # Protocol specification
│   ├── quickstart/Geneclaw-Runbook.md
│   ├── ops/first-live-run-*.md # Audit records
│   └── devlog/                 # Daily development logs
└── .github/
    ├── workflows/ci.yml        # CI pipeline
    └── pull_request_template.md
```

## Install

**From source (recommended)**

```bash
git clone https://github.com/Clawland-AI/Geneclaw.git
cd Geneclaw
pip install -e ".[dev]"
```

**Add upstream remote** (for syncing with nanobot)

```bash
git remote add upstream https://github.com/HKUDS/nanobot.git
```

## Quick Start

### 1. Initialize

```bash
nanobot onboard
```

### 2. Enable Geneclaw

Add or merge into `~/.nanobot/config.json`:

```json
{
  "geneclaw": {
    "enabled": true,
    "redactEnabled": true,
    "allowApplyDefault": false,
    "allowlistPaths": ["geneclaw/", "docs/"],
    "denylistPaths": [".env", "secrets/", ".git/", "config.json"],
    "maxPatchLines": 500
  }
}
```

### 3. Verify

```bash
nanobot geneclaw doctor
```

### 4. Chat (generates run events)

```bash
nanobot agent -m "Hello, what tools do you have?"
```

### 5. Generate evolution proposal

```bash
nanobot geneclaw evolve --dry-run
```

### 6. View statistics

```bash
nanobot geneclaw report
```

## CLI Reference

All commands are under `nanobot geneclaw`:

| Command | Description |
|---------|-------------|
| `nanobot geneclaw doctor` | Health checks — config, paths, permissions |
| `nanobot geneclaw status` | Current state — enabled, sessions, last run |
| `nanobot geneclaw evolve --dry-run` | Generate evolution proposal (dry-run default) |
| `nanobot geneclaw evolve --apply` | Generate and apply proposal (requires config) |
| `nanobot geneclaw apply <file.json>` | Apply a saved proposal file |
| `nanobot geneclaw report` | Pipeline statistics (table) |
| `nanobot geneclaw report --format json` | Pipeline statistics (JSON) |
| `nanobot geneclaw autopilot` | Multi-cycle evolution loop |
| `nanobot geneclaw benchmark` | Pipeline performance benchmarks |

### Autopilot Options

```bash
nanobot geneclaw autopilot \
  --max-cycles 5 \
  --cooldown 10 \
  --auto-approve low \
  --dry-run \
  --format table
```

| Option | Default | Description |
|--------|---------|-------------|
| `--max-cycles` | 3 | Maximum evolution cycles |
| `--cooldown` | 5.0 | Seconds between cycles |
| `--auto-approve` | low | Risk threshold for auto-approve (`none`, `low`) |
| `--dry-run/--apply` | dry-run | Apply mode requires `allow_apply_default=true` |
| `--stop-on-failure/--continue` | stop | Halt on first apply failure |
| `--format` | table | Output format (`table`, `json`) |

### Benchmark Options

```bash
nanobot geneclaw benchmark \
  --event-counts 100,500,1000 \
  --gate-iterations 100 \
  --format table
```

## Configuration

The `geneclaw` section in `~/.nanobot/config.json`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable geneclaw observability + evolution |
| `logMaxChars` | int | `500` | Max chars per event preview |
| `redactEnabled` | bool | `true` | Redact secrets in all logs |
| `allowApplyDefault` | bool | `false` | Must be `true` to allow `--apply` |
| `allowlistPaths` | list | `["geneclaw/", "nanobot/", "tests/", "docs/"]` | Paths proposals may modify |
| `denylistPaths` | list | `[".env", "secrets/", ".git/", "config.json"]` | Paths that are always blocked |
| `maxPatchLines` | int | `500` | Maximum diff lines allowed |

## Safety Model

Geneclaw enforces multiple layers of protection:

### 1. Dry-Run Default

All commands default to `--dry-run`. Proposals are generated and validated but never applied without explicit `--apply` flag AND `allowApplyDefault=true` in config.

### 2. Gatekeeper (5 Checks)

Every proposal must pass all five checks before application:

| Check | What it does |
|-------|-------------|
| **Path Allowlist** | All `files_touched` must start with an allowed prefix |
| **Path Denylist** | No file may match a denied path (`.env`, `secrets/`, etc.) |
| **Diff Size Limit** | Line count must not exceed `maxPatchLines` |
| **Secret Scan** | Diff is scanned for API keys, tokens, PEM keys |
| **Code Pattern Scan** | Detects `eval()`, `exec()`, `os.system()`, `subprocess.call()` |

### 3. Git Safety

- Creates a dedicated `evo/<timestamp>-<slug>` branch
- Runs `git apply --check` before actual application
- Executes `pytest -q` after patching
- Automatic rollback on test failure (branch deleted, previous state restored)

### 4. Secret Redaction

All event logs (run events + evolution events) pass through regex-based redaction before being written to disk. Patterns include API keys, tokens, passwords, PEM blocks, and Bearer tokens.

### 5. Recommended Allowlist Strategy

Start minimal and expand only after successful, reviewed evolution cycles:

| Phase | Allowlist | When |
|-------|-----------|------|
| **Bootstrap** | `geneclaw/`, `docs/` | Day 1 |
| **Expanded** | + `tests/` | After 5+ reviewed proposals |
| **Full** | + `nanobot/` | After 20+ reviewed proposals |

See `docs/specs/GEP-v0.md` Section 10 for the complete strategy.

## Slash Command

When chatting with the agent, use `/evolve` to trigger an in-conversation evolution analysis:

```
You: /evolve
Bot: Evolution analysis started in background. Results will be posted shortly.
Bot: [Evolution Proposal: ...] (always dry-run, never auto-applies)
```

## Data Layout

All runtime data lives under the nanobot workspace (`~/.nanobot/workspace/`):

```
~/.nanobot/workspace/geneclaw/
├── runs/                      # Run event logs (per session, per day)
│   └── <session_key>/
│       └── YYYYMMDD.jsonl
├── events/                    # Evolution lifecycle events
│   └── events.jsonl
└── proposals/                 # Generated proposals
    └── proposal_YYYYMMDD_HHMMSS.json
```

## Testing

```bash
# Run all geneclaw tests
pytest tests/test_geneclaw_*.py -q

# Run full test suite
pytest -q
```

Current test coverage: **54 tests** across 6 test files.

## Development

### Upstream Sync

```bash
git fetch upstream
git merge upstream/main --no-edit
# resolve conflicts if any
```

### Branch Naming

| Prefix | Purpose |
|--------|---------|
| `feat/<topic>` | New features |
| `fix/<topic>` | Bug fixes |
| `chore/<topic>` | Maintenance |
| `evo/<timestamp>-<slug>` | Auto-generated by evolution engine |

### Commit Convention

```
feat(geneclaw): add autopilot controller

Evo-Event-ID: abc123
Risk-Level: low
Tests: pytest tests/test_geneclaw_autopilot.py -q
```

## Specifications

- [GEP v0 Protocol Specification](docs/specs/GEP-v0.md)
- [Operator Runbook](docs/quickstart/Geneclaw-Runbook.md)
- [First Live Run Audit](docs/ops/first-live-run-2026-02-18.md)
- [Development Log](docs/devlog/2026-02-18.md)

## Repository

| | |
|-|-|
| **Origin** | [Clawland-AI/Geneclaw](https://github.com/Clawland-AI/Geneclaw) |
| **Upstream** | [HKUDS/nanobot](https://github.com/HKUDS/nanobot) |
| **Organization** | [Clawland-AI](https://github.com/Clawland-AI) |

## License

MIT — see [LICENSE](LICENSE).

<p align="center">
  <sub>Geneclaw is built by <a href="https://github.com/Clawland-AI">Clawland-AI</a> on top of <a href="https://github.com/HKUDS/nanobot">HKUDS/nanobot</a></sub>
</p>
