# First Real Proposal — From Zero to LLM-Generated Evolution

> Step-by-step guide to generating your first non-trivial evolution proposal
> using a real LLM provider. Covers setup, event generation, proposal review,
> and the decision to apply or discard.

**Prerequisites:**
- Geneclaw installed (`pip install -e ".[dev]"`)
- `nanobot onboard` completed
- LLM provider configured (see [LLM Provider Setup](llm-provider-setup.md))

---

## Step 1: Export Your API Key

```bash
# Linux/macOS
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"

# Windows PowerShell
$env:OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
```

Ensure the key is also set in `~/.nanobot/config.json` under `providers`.

---

## Step 2: Verify Configuration

```bash
nanobot geneclaw doctor
```

**Expected output (all green):**
```
✓ geneclaw.enabled
✓ dry_run_default
✓ runs_dir_writable
✓ allowlist_paths
✓ denylist_paths
✓ redact_enabled

Summary: 6 ok, 0-1 warnings, 0 errors
```

Fix any errors before proceeding. Warnings about `restrictToWorkspace` are
acceptable for initial testing but should be addressed for production.

---

## Step 3: Generate Run Events

Interact with the agent to create observable events — including some that
are likely to fail (this gives the evolver something to diagnose):

```bash
# Successful interaction
nanobot agent -m "What tools do you have? List them."

# Interaction that may produce tool failures
nanobot agent -m "Search the web for 'geneclaw evolution protocol' and summarize."

# Another interaction to build history
nanobot agent -m "Read the file geneclaw/models.py and explain the data models."
```

Verify events were recorded:

```bash
nanobot geneclaw status
```

You should see `Sessions recorded: ≥1` and a recent `Last run log` timestamp.

---

## Step 4: Generate Evolution Proposal (Dry-Run)

```bash
nanobot geneclaw evolve --dry-run
```

**Expected output (with LLM provider):**
```
Analysing recent events...

Evolution Proposal: <meaningful title>
  ID:         <uuid>
  Objective:  <description of what the proposal fixes/improves>
  Risk:       low|medium|high
  Files:      geneclaw/recorder.py, ...
  Evidence:   <failure analysis>
  Diff lines: <N>

Proposal written to ~/.nanobot/workspace/geneclaw/proposals/proposal_YYYYMMDD_HHMMSS.json

Dry-run mode. Use --apply to apply the proposal.
```

If you see `heuristic-only` instead of a real proposal, your LLM provider
is not configured correctly. Go back to Step 1.

---

## Step 5: Review Pipeline Statistics

```bash
# Table format
nanobot geneclaw report

# JSON format (for scripting / archival)
nanobot geneclaw report --format json
```

Review:
- `Proposals generated` — should be ≥1
- `Risk Distribution` — what risk levels are being generated
- `Top Tool Failures` — what the evolver is diagnosing

---

## Step 6: Review the Proposal

### 6.1 Read the Proposal JSON

```bash
# Find the latest proposal
ls ~/.nanobot/workspace/geneclaw/proposals/

# Read it (replace with actual filename)
cat ~/.nanobot/workspace/geneclaw/proposals/proposal_YYYYMMDD_HHMMSS.json
```

### 6.2 Review Checklist

- [ ] **Title & Objective** — Does it make sense? Is it addressing a real issue?
- [ ] **Risk Level** — Is it accurate? Low-risk proposals should be minor fixes.
- [ ] **Files Touched** — Are they within the allowlist? (`geneclaw/`, `docs/`)
- [ ] **Unified Diff** — Read the actual code changes line by line:
  - Does it introduce any security issues?
  - Does it break existing functionality?
  - Is the code quality acceptable?
- [ ] **Tests to Run** — Are appropriate tests listed?
- [ ] **Rollback Plan** — Is it actionable?

### 6.3 Decision Matrix

| Condition | Action |
|-----------|--------|
| Proposal is `no-op` or `heuristic-only` | Discard; no action needed |
| Risk = `low`, diff is small, files in allowlist | Consider applying (Step 7) |
| Risk = `medium`, complex diff | Review carefully; discuss with team if applicable |
| Risk = `high` or touches critical files | Discard or request manual implementation |
| Diff contains `eval()`, `exec()`, etc. | Reject immediately |
| Diff touches files outside allowlist | Reject — gatekeeper should have caught this |

---

## Step 7: Apply (Only If Approved)

**Only proceed if the proposal passes all review checks.**

### Option A: Apply via CLI (creates git branch)

```bash
nanobot geneclaw apply \
  ~/.nanobot/workspace/geneclaw/proposals/proposal_YYYYMMDD_HHMMSS.json \
  --apply
```

This will:
1. Validate through gatekeeper (again)
2. Create `evo/<timestamp>-<slug>` branch
3. Apply the unified diff
4. Run `pytest -q`
5. If tests pass → commit; if fail → auto-rollback

### Option B: Manual Apply (more control)

```bash
# Create a branch
git checkout -b feat/first-real-proposal

# Apply the diff manually
git apply path/to/extracted.patch

# Run tests
pytest -q

# If all pass, commit
git add -A
git commit -m "feat(geneclaw): <proposal title>

Evo-Event-ID: <proposal-id>
Risk-Level: low
Tests: pytest -q"

# Push and open PR
git push -u origin feat/first-real-proposal
gh pr create --title "<proposal title>" --body "Generated by geneclaw evolve"
```

---

## Safety Constraints (Initial Phase)

These constraints must be enforced during the initial trust-building period:

| Constraint | Value | Rationale |
|------------|-------|-----------|
| **Allowlist** | `geneclaw/`, `docs/` only | Evolver can only modify its own code + docs |
| **Denylist** | `.env`, `secrets/`, `.git/`, `config.json`, `pyproject.toml` | Critical files always blocked |
| **Max Diff Lines** | 500 (default) | Prevents oversized patches |
| **Risk Level** | Only apply `low` risk proposals | Higher risk requires human implementation |
| **Apply Mode** | `--dry-run` default | Must explicitly opt-in to `--apply` |

See [GEP-v0.md Section 10](../specs/GEP-v0.md) for the phased allowlist
expansion strategy.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No LLM provider — heuristic-only mode` | Configure API key (see [LLM Provider Setup](llm-provider-setup.md)) |
| Proposal is always `no-op` | Generate more run events with failures (Step 3) |
| `Gatekeeper rejected proposal` | Check the rejection reasons; files may be outside allowlist |
| `Patch apply --check failed` | Diff may be stale; regenerate with `evolve --dry-run` |
| `Tests failed after apply — rolled back` | Review test output; the proposal may have introduced a bug |
| `allow_apply_default=false` blocks apply | Set `geneclaw.allowApplyDefault: true` in config (understand the risk) |
