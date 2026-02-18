# Changelog

All notable changes to the Geneclaw project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.1.0] — 2026-02-18

**Initial release of the Geneclaw Evolution Protocol (GEP v0).**

Repository: [Clawland-AI/Geneclaw](https://github.com/Clawland-AI/Geneclaw)
Upstream: [HKUDS/nanobot](https://github.com/HKUDS/nanobot)

### Added

#### M1 — Observability / Run Recorder
- `geneclaw/recorder.py` — JSONL event recorder scoped per session per day
- `geneclaw/redact.py` — Regex-based secret redaction (API keys, tokens, PEM blocks, Bearer)
- `geneclaw/models.py` — `RunEvent` Pydantic model
- Integration into `nanobot/agent/loop.py` — records inbound/outbound messages, tool start/end, exceptions
- `GeneclawConfig` added to `nanobot/config/schema.py`

#### M2 — Evolver (Proposal Generator)
- `geneclaw/evolver.py` — Heuristic diagnosis + LLM-assisted evolution proposal generation
- `json_repair` integration for robust JSON parsing from LLM output
- Minimal no-op fallback when LLM output is invalid or unavailable
- `geneclaw/models.py` — `EvolutionProposal` model (JSON + unified diff)

#### M3 — Gatekeeper + Apply + CLI
- `geneclaw/gatekeeper.py` — 5-layer safety validation:
  - Path allowlist / denylist
  - Diff size limit (`max_patch_lines`)
  - Secret scan in diffs
  - Suspicious code pattern detection (`eval`, `exec`, `os.system`, `subprocess.call`)
- `geneclaw/apply.py` — Git-branched unified diff application with:
  - `evo/<timestamp>-<slug>` branch creation
  - `git apply --check` pre-validation
  - `pytest -q` post-apply test execution
  - Automatic rollback on test failure
- `geneclaw/cli.py` — Typer CLI subcommands: `status`, `evolve`, `apply`
- Registered `nanobot geneclaw` CLI group

#### M4 — Operationalization & Governance
- `geneclaw/doctor.py` — 8 read-only health checks with actionable suggestions
- `geneclaw/event_store.py` — Append-only JSONL evolution lifecycle event log with redaction
- `geneclaw/report.py` — Aggregated pipeline statistics (evolve/apply counts, success rate, risk distribution)
- `geneclaw/models.py` — `EvoEvent` model for evolution lifecycle tracking
- CLI commands: `doctor`, `report`
- `/evolve` slash command in agent loop (background task, always dry-run)
- `.github/workflows/ci.yml` — CI pipeline (Python 3.11/3.12/3.13, pytest, ruff)
- `.github/pull_request_template.md` — Structured PR review template
- `docs/quickstart/Geneclaw-Runbook.md` — Operator runbook
- `docs/specs/GEP-v0.md` — Protocol specification

#### P0 — Live Run-through
- End-to-end validation: doctor → status → simulated events → evolve → report
- `docs/ops/first-live-run-2026-02-18.md` — Auditable run record

#### P1 — Governance Hardening
- `report --format json` option with `ReportData.to_dict()`
- Event store path hint in table report output
- Graceful heuristic-only fallback when no LLM provider configured
- 3-phase allowlist strategy documented in GEP-v0.md Section 10

#### M5 — Autopilot + Benchmarks
- `geneclaw/autopilot.py` — Multi-cycle evolution loop controller:
  - Configurable cycles, cooldown, risk-based auto-approve
  - Dry-run default, stop-on-failure option
  - Event recording at each stage
- `geneclaw/benchmarks.py` — Pipeline performance benchmarking:
  - Synthetic event generation + diagnosis timing
  - Gatekeeper validation timing (normal + large diff)
  - Event store write/read throughput
- CLI commands: `autopilot`, `benchmark` (both with `--format json`)

### Testing
- 54 geneclaw-specific tests across 6 test files
- All tests passing on Python 3.11+

### Security
- All event logs redacted before writing to disk
- Dry-run default at config level (`allow_apply_default=false`) and CLI level (`--dry-run`)
- Gatekeeper enforces allowlist/denylist/secret-scan/code-pattern-scan
- Git safety: branching, pre-check, post-test, auto-rollback

---

[v0.1.0]: https://github.com/Clawland-AI/Geneclaw/releases/tag/v0.1.0
