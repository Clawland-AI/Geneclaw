# Release Runbook — Clawland-AI/Geneclaw

> Step-by-step guide for tagging, creating a GitHub Release, and verifying.

**Repository:** https://github.com/Clawland-AI/Geneclaw

---

## 1. Pre-Release Checklist

Before creating a release, verify all of the following:

```bash
# 1. Ensure you're on master and up to date
git checkout master
git pull origin master

# 2. Run full test suite
pytest -q

# 3. Run geneclaw health checks
nanobot geneclaw doctor

# 4. Run evolve dry-run to verify pipeline
nanobot geneclaw evolve --dry-run

# 5. Check report for any anomalies
nanobot geneclaw report

# 6. Run benchmarks (baseline for this release)
nanobot geneclaw benchmark --format json > benchmark-v0.1.0.json
```

All tests must pass. Doctor must show 0 errors. Evolve must complete without crash.

---

## 2. Update CHANGELOG

1. Open `CHANGELOG.md` in the repository root
2. Ensure the version section (e.g., `## [v0.1.0]`) is complete
3. Verify the release date is correct
4. Commit if changes were needed:

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for v0.1.0"
git push origin master
```

---

## 3. Create Git Tag

```bash
# Create annotated tag
git tag -a v0.1.0 -m "Geneclaw v0.1.0 — GEP v0 initial release

Features:
- Observability: JSONL run event recorder with secret redaction
- Evolver: heuristic + LLM-assisted evolution proposals
- Gatekeeper: 5-layer safety validation
- Apply: git-branched diff application with auto-rollback
- Autopilot: multi-cycle evolution loop controller
- Benchmarks: pipeline performance measurement
- Doctor: read-only health checks
- Report: aggregated pipeline statistics (table + JSON)
- CI/CD: GitHub Actions workflow + PR template

54 tests passing. All dry-run by default."

# Push the tag
git push origin v0.1.0
```

---

## 4. Create GitHub Release

### Option A: Using `gh` CLI (recommended)

```bash
gh release create v0.1.0 \
  --title "Geneclaw v0.1.0 — GEP v0 Initial Release" \
  --notes-file CHANGELOG.md \
  --latest
```

### Option B: Using GitHub Web UI

1. Go to https://github.com/Clawland-AI/Geneclaw/releases/new
2. **Choose a tag:** Select `v0.1.0`
3. **Release title:** `Geneclaw v0.1.0 — GEP v0 Initial Release`
4. **Description:** Copy the `## [v0.1.0]` section from `CHANGELOG.md`
5. Check **Set as the latest release**
6. Click **Publish release**

> GitHub automatically generates source archives (`.tar.gz` and `.zip`)
> for every release. No manual upload needed.

---

## 5. Post-Release Verification

After the release is published:

```bash
# 1. Verify tag exists on remote
git ls-remote --tags origin | grep v0.1.0

# 2. Verify release page
gh release view v0.1.0

# 3. Verify CI ran on the tag push (check GitHub Actions)
gh run list --limit 3
```

---

## 6. Rollback (if needed)

If a critical issue is found after release:

```bash
# Delete the GitHub Release
gh release delete v0.1.0 --yes

# Delete the remote tag
git push origin --delete v0.1.0

# Delete the local tag
git tag -d v0.1.0

# Fix the issue, then re-release with the same or bumped version
```

---

## 7. Version Bumping Guide

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| Bug fix, docs, minor improvement | Patch | `v0.1.0` → `v0.1.1` |
| New feature, non-breaking | Minor | `v0.1.0` → `v0.2.0` |
| Breaking change | Major | `v0.1.0` → `v1.0.0` |

Update these files when bumping:
- `geneclaw/__init__.py` — `__version__`
- `CHANGELOG.md` — new section
- `pyproject.toml` — `version` field (if publishing to PyPI)

---

## 8. Future: Automated Release Pipeline

When the project matures to need automated releases (e.g., PyPI publish,
Docker image build), add `.github/workflows/release.yml`:

- **Trigger:** `push` with `tags: ["v*"]`
- **Steps:** build → test → publish source archive → notify
- **Guards:** require CI pass, never include secrets in artifacts
- **Timeline:** implement when PyPI or Docker publishing is needed

For now, manual releases via `gh release create` are sufficient and provide
full human control over what gets published.
