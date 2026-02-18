# Hacker News — Show HN Post

## Title

Show HN: Geneclaw – An AI agent framework that safely evolves its own code

## URL

https://github.com/Clawland-AI/Geneclaw

## Text (if self-post)

Hi HN,

We built Geneclaw, an open-source AI agent framework with a built-in self-evolution engine. The core idea: instead of only executing tasks for users, the agent continuously observes its own runtime failures, diagnoses root causes, generates constrained code patches, and (optionally) applies them — all behind a 5-layer safety gatekeeper.

Key design decisions:

- **Dry-run by default.** Nothing is applied without explicit human approval.
- **5-layer Gatekeeper:** Path allowlist/denylist, diff size limits, secret scanning, and code pattern detection (blocks eval/exec/os.system).
- **Git safety:** Every patch creates a dedicated branch, runs `git apply --check` first, executes tests after patching, and automatically rolls back on failure.
- **Full audit trail:** Every event in the evolution lifecycle is logged as append-only JSONL with secret redaction. A Streamlit dashboard visualises the data.
- **LLM-optional:** Works in heuristic-only mode without any LLM provider configured.

Geneclaw is built on top of nanobot (https://github.com/HKUDS/nanobot), a lightweight personal AI agent framework from HKU.

The evolution pipeline: Observe → Diagnose → Propose → Gate → Apply

We've been running it on our own codebase with the evolution restricted to `geneclaw/` and `docs/` directories only. After 20+ reviewed proposals, we'll expand to the full repo.

Architecture and quick start: https://geneclaw.ai
Protocol spec: https://github.com/Clawland-AI/Geneclaw/blob/master/docs/specs/GEP-v0.md

We'd love feedback on the safety model — is 5 layers enough? Too much? What would you want before letting an AI agent modify its own code?

---

## Posting Notes

- Best posting time: US weekday mornings (9-11am ET), Tuesday-Thursday
- Tag: Show HN
- Engage with comments promptly in the first 2 hours
