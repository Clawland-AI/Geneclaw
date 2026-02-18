# Reddit — Launch Posts

---

## Post 1: r/MachineLearning

### Title

[P] Geneclaw: Open-source AI agent framework with safe self-evolution — agents observe failures, generate patches, apply behind 5-layer gatekeeper

### Body

**TL;DR:** We open-sourced an AI agent framework where the agent can evolve its own code through a closed-loop pipeline: Observe → Diagnose → Propose → Gate → Apply. Everything is dry-run by default with a 5-layer safety gatekeeper.

**Problem:** Current AI agents execute tasks but can't learn from their own operational failures. When a tool call fails or an exception occurs repeatedly, a human has to diagnose and fix it.

**Solution:** Geneclaw adds a self-evolution engine on top of [nanobot](https://github.com/HKUDS/nanobot) (a lightweight agent from HKU). The agent records all runtime events, diagnoses failure patterns, generates constrained evolution proposals (JSON + unified diffs), validates them through 5 safety checks, and applies them via git with automated testing and rollback.

**Safety model (the interesting part):**
- Dry-run default at both config and CLI level
- Gatekeeper: path allowlist/denylist, diff size limit, secret scan, code pattern detection
- Git safety: dedicated branch, pre-check, post-test, auto-rollback
- Full audit trail: append-only JSONL with secret redaction
- Recommended: start with minimal allowlist (`geneclaw/`, `docs/` only), expand after reviewed cycles

**Features:**
- Works without LLM (heuristic-only fallback)
- Multi-cycle autopilot with configurable risk thresholds
- Streamlit dashboard for visual audit
- 123 tests, CI pipeline, comprehensive docs

**Links:**
- Website: https://geneclaw.ai
- GitHub: https://github.com/Clawland-AI/Geneclaw
- Protocol spec: https://github.com/Clawland-AI/Geneclaw/blob/master/docs/specs/GEP-v0.md

Happy to answer any questions about the safety model or architecture.

---

## Post 2: r/LocalLLaMA

### Title

Geneclaw: self-evolving AI agent that works locally without any API keys (heuristic-only mode)

### Body

Built an open-source agent framework called Geneclaw that adds self-evolution to [nanobot](https://github.com/HKUDS/nanobot).

The cool part for this community: **it works completely locally without any API keys.** The heuristic diagnosis engine analyses runtime failure patterns and generates evolution proposals without needing an LLM.

When you DO have a local LLM (Ollama, llama.cpp, etc.), it uses it for deeper root cause analysis and smarter proposals — but the basic pipeline runs without one.

Pipeline: Observe → Diagnose → Propose → Gate → Apply

Safety: 5-layer gatekeeper, dry-run by default, git-branched application with auto-rollback.

Quick start:
```
git clone https://github.com/Clawland-AI/Geneclaw.git
pip install -e ".[dev]"
nanobot onboard
nanobot geneclaw doctor
nanobot geneclaw evolve --dry-run
```

GitHub: https://github.com/Clawland-AI/Geneclaw
Website: https://geneclaw.ai

---

## Post 3: r/artificial

### Title

We built an AI agent that can safely fix its own bugs — here's the safety model we designed

### Body

The question "should AI systems modify their own code?" is usually a thought experiment. We made it practical with Geneclaw, an open-source framework where agents evolve through a controlled pipeline.

The safety model is the core contribution:

1. **Dry-run default** — Nothing applies without explicit human approval
2. **5-layer gatekeeper** — Path allowlist/denylist, diff size limits, secret scanning, code pattern detection (blocks eval/exec)
3. **Git safety** — Every patch on a dedicated branch, pre-validated, tested, auto-rolled back on failure
4. **Audit trail** — Every event logged as append-only JSONL with secret redaction
5. **Graduated trust** — Start allowing changes only in safe directories, expand after reviewed cycles

We think self-evolution is inevitable for AI systems but needs to be built with security as the primary constraint, not an afterthought.

Would love the community's perspective: what safety properties would you want before deploying something like this in production?

GitHub: https://github.com/Clawland-AI/Geneclaw
Website: https://geneclaw.ai

---

## Posting Notes

- r/MachineLearning: Use [P] tag for project posts
- Best time: Monday-Thursday, 10am-1pm ET
- Cross-post to r/Python with [Project] focus on the tooling/CLI
- Engage with comments actively — Reddit rewards early responses
