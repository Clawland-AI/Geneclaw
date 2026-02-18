# First Live Run — 2026-02-18

> Auditable record of the first end-to-end Geneclaw (GEP v0) run.
> Repository: Clawland-AI/Geneclaw | Upstream: HKUDS/nanobot

---

## 1. Git Remotes

```
origin  https://github.com/Clawland-AI/Geneclaw.git (fetch)
origin  https://github.com/Clawland-AI/Geneclaw.git (push)
upstream        https://github.com/HKUDS/nanobot.git (fetch)
upstream        https://github.com/HKUDS/nanobot.git (push)
```

## 2. Config Enablement

- `geneclaw.enabled` set to `true` in `~/.nanobot/config.json`
- `allow_apply_default` = `false` (dry-run by default, safe)
- `redact_enabled` = `true`
- `allowlist_paths` = `["geneclaw/", "nanobot/", "tests/", "docs/"]`
- `denylist_paths` = `[".env", "secrets/", ".git/", "config.json"]`
- `max_patch_lines` = `500`

## 3. `nanobot geneclaw doctor`

```
Geneclaw Doctor

  ✓ geneclaw.enabled: Geneclaw observability is enabled.
  ✓ dry_run_default: Dry-run is the default (allow_apply_default=false). Safe.
  ⚠ restrict_to_workspace: tools.restrictToWorkspace is OFF. Strongly
    recommended to enable for geneclaw workflows.
  ✓ runs_dir_writable: Runs directory does not exist yet (auto-created on first event).
  ✓ allowlist_paths: Allowlist (4 entries): geneclaw/, nanobot/, tests/, docs/
  ✓ denylist_paths: Denylist (4 entries): .env, secrets/, .git/, config.json
  ✓ redact_enabled: Secret redaction is enabled for run logs.

  Summary: 6 ok, 1 warnings, 0 errors
```

## 4. `nanobot geneclaw status`

```
Geneclaw Status

  Enabled:           yes
  Redact:            True
  Allow apply:       False
  Max patch lines:   500
  Sessions recorded: 1
  Last run log:      2026-02-18T01:37:19.833115+00:00
```

## 5. Simulated Agent Interactions

Created session `sim-p0-demo` with 17 run events:

| Type | Count | Notes |
|------|-------|-------|
| inbound_msg | 2 | Successful + failing conversation |
| tool_start | 5 | exec_command, read_file, web_search ×2, exec_command |
| tool_end | 5 | 2 success, 3 failures |
| exception | 3 | TimeoutError, ConnectionError, CalledProcessError |
| outbound_msg | 2 | Success + error response |

## 6. `nanobot geneclaw evolve --dry-run`

```
No LLM provider configured — running heuristic-only mode.
Analysing recent events...

Evolution Proposal: heuristic-only
  ID:         b931ef32-f329-4fab-b5a2-85fece2d8e66
  Objective:  Heuristic diagnosis (no LLM): Top failing tools: web_search(2),
              exec_command(1); Exception clusters: "TimeoutError: web search
              timed out after 30s"(1), "ConnectionError: DNS lookup failed for
              search.api"(1), "CalledProcessError: command exited with code 1"(1)
  Risk:       low
  Files:      (none)
  Evidence:   Top failing tools: web_search(2), exec_command(1); ...

Proposal written to ~/.nanobot/workspace/geneclaw/proposals/proposal_20260218_013923.json

Dry-run mode. Use --apply to apply the proposal.
```

## 7. `nanobot geneclaw report`

```
Geneclaw Report (last 24.0h)

      Evolution Pipeline
┌─────────────────────┬───────┐
│ Metric              │ Value │
├─────────────────────┼───────┤
│ Proposals generated │ 1     │
│ Apply attempted     │ 0     │
│ Apply succeeded     │ 0     │
│ Apply failed        │ 0     │
│ Success rate        │ N/A   │
└─────────────────────┴───────┘

Risk Distribution
       low: █ (1)

Top Tool Failures (from run logs)
    2x  web_search
    1x  exec_command

Top Exceptions (from run logs)
    1x  TimeoutError: web search timed out after 30s
    1x  ConnectionError: DNS lookup failed for search.api
    1x  CalledProcessError: command exited with code 1
```

## 8. `pytest -q` (geneclaw tests)

```
........................................  [100%]
40 passed in 1.41s
```

## 9. Summary

| Step | Status | Notes |
|------|--------|-------|
| Git remotes | ✓ | origin=Clawland-AI, upstream=HKUDS |
| Config enabled | ✓ | geneclaw.enabled=true, safe defaults |
| Doctor | ✓ | 6 ok / 1 warn (restrictToWorkspace) |
| Status | ✓ | 1 session, last run logged |
| Simulated events | ✓ | 17 events with failures |
| Evolve (dry-run) | ✓ | Heuristic-only fallback works |
| Report | ✓ | Pipeline + risk + tool failures displayed |
| Pytest | ✓ | 40/40 pass |

**Conclusion**: GEP v0 end-to-end pipeline is operational. The heuristic-only
fallback gracefully handles the no-LLM-provider case. When an LLM provider API
key is configured, `evolve` will produce LLM-assisted proposals with diffs.
