# Upstream Sync Strategy — HKUDS/nanobot → Clawland-AI/Geneclaw

> How to keep Geneclaw synchronized with the upstream nanobot repository.

**Origin:** `Clawland-AI/Geneclaw` (our fork with GEP v0)
**Upstream:** `HKUDS/nanobot` (original nanobot framework)

---

## 1. Prerequisites

Verify your remotes are correctly configured:

```bash
git remote -v
```

**Expected:**
```
origin    https://github.com/Clawland-AI/Geneclaw.git (fetch)
origin    https://github.com/Clawland-AI/Geneclaw.git (push)
upstream  https://github.com/HKUDS/nanobot.git (fetch)
upstream  https://github.com/HKUDS/nanobot.git (push)
```

If `upstream` is missing:

```bash
git remote add upstream https://github.com/HKUDS/nanobot.git
```

---

## 2. Sync Procedure

### Step 1: Ensure Clean Working Tree

```bash
git status
# Must show: "nothing to commit, working tree clean"
# If not, stash or commit your changes first
```

### Step 2: Fetch Upstream

```bash
git fetch upstream
```

### Step 3: Merge Upstream into Master

```bash
git checkout master
git merge upstream/main --no-edit
```

> **Note:** Upstream uses `main` as default branch. We use `master`.
> If upstream switches branch names, adjust accordingly.

### Step 4: Resolve Conflicts (if any)

See Section 3 for conflict resolution strategy.

### Step 5: Run Regression Tests

```bash
# Full test suite
pytest -q

# Geneclaw health check
nanobot geneclaw doctor

# Benchmark (compare with previous baseline)
nanobot geneclaw benchmark --format json

# Evolve dry-run (verify pipeline still works)
nanobot geneclaw evolve --dry-run
```

All tests must pass before pushing.

### Step 6: Push

```bash
git push origin master
```

---

## 3. Conflict Resolution Strategy

Conflicts are expected because Geneclaw modifies several nanobot files.
Handle them by category:

### 3.1 Geneclaw-Only Files (always keep ours)

These files exist only in Geneclaw and should never conflict:

```
geneclaw/**
tests/test_geneclaw_*
docs/specs/GEP-v0.md
docs/quickstart/Geneclaw-Runbook.md
docs/ops/**
docs/devlog/**
.github/pull_request_template.md
CHANGELOG.md
.cursorrules
```

If git reports conflicts in these files (unlikely), keep our version:

```bash
git checkout --ours <file>
git add <file>
```

### 3.2 Modified Nanobot Files (review hunk by hunk)

These nanobot files were modified by Geneclaw and may conflict:

| File | Our Changes | Strategy |
|------|-------------|----------|
| `nanobot/agent/loop.py` | RunRecorder integration, `/evolve` handler | Keep our additions; accept upstream changes elsewhere |
| `nanobot/cli/commands.py` | `geneclaw_config` param, CLI registration | Keep our additions; accept upstream changes elsewhere |
| `nanobot/config/schema.py` | `GeneclawConfig` model + field | Keep our additions; accept upstream changes elsewhere |
| `pyproject.toml` | `geneclaw` in packages/includes | Keep our additions; accept upstream changes elsewhere |
| `.gitignore` | Removed `docs/`, `tests/` exclusions | Keep ours |
| `README.md` | Completely replaced | Keep ours |

For each conflicted file:

```bash
# Open in editor and resolve manually
# Look for <<<<<<< HEAD / ======= / >>>>>>> upstream/main markers

# After resolving:
git add <file>
```

**Principle:** Accept all upstream changes that don't conflict with our
Geneclaw integrations. For our integration points (recorder hooks, CLI
registration, config schema), preserve our additions and merge upstream
changes around them.

### 3.3 Unmodified Nanobot Files (always accept upstream)

All other nanobot files that we haven't modified:

```bash
git checkout --theirs <file>
git add <file>
```

### 3.4 Complete the Merge

```bash
# After all conflicts are resolved
git commit
# The default merge commit message is fine
```

---

## 4. Post-Sync Verification

After a successful merge, run this full verification sequence:

```bash
# 1. Test suite
pytest -q
# Expected: all tests pass (including geneclaw tests)

# 2. Doctor check
nanobot geneclaw doctor
# Expected: 0 errors

# 3. Benchmark comparison
nanobot geneclaw benchmark --format json > benchmark-post-sync.json
# Compare with previous baseline — significant regressions need investigation

# 4. Evolve pipeline check
nanobot geneclaw evolve --dry-run
# Expected: completes without error

# 5. Report check
nanobot geneclaw report
# Expected: displays without error
```

---

## 5. Sync Frequency

| Trigger | Action |
|---------|--------|
| **Weekly (routine)** | Fetch + check for new commits; merge if any |
| **Upstream breaking change** | Sync immediately, resolve conflicts, update integration points |
| **Before a Geneclaw release** | Sync to ensure we're on latest upstream |
| **After major Geneclaw feature** | Sync to verify no upstream conflicts with new code |

---

## 6. Troubleshooting

| Problem | Solution |
|---------|----------|
| `fatal: refusing to merge unrelated histories` | Add `--allow-unrelated-histories` flag (first sync only) |
| Massive conflicts in `nanobot/agent/loop.py` | Compare our integration points line by line; upstream may have restructured |
| Tests fail after merge | Check if upstream changed APIs that our integration uses |
| `geneclaw doctor` shows new errors | Upstream may have changed config schema; update `GeneclawConfig` |
| Benchmark shows regression | Compare before/after; may be upstream dependency change |

---

## 7. Emergency: Abort a Bad Merge

If a merge goes wrong and you haven't pushed yet:

```bash
# Abort in-progress merge
git merge --abort

# Or reset to pre-merge state
git reset --hard HEAD
```

If you already pushed a bad merge:

```bash
# Revert the merge commit (creates a new commit that undoes it)
git revert -m 1 <merge-commit-hash>
git push origin master
```

> **Never force-push master.** Branch protection should prevent this,
> but even without protection, always revert instead of force-pushing.
