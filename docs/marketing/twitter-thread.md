# Twitter/X — Launch Thread

## Tweet 1 (Hook)

🧬 We built an AI agent that safely evolves its own code.

Geneclaw is an open-source framework where agents:
→ Observe their own failures
→ Diagnose root causes  
→ Generate constrained patches
→ Apply them behind a 5-layer safety gatekeeper

Everything is dry-run by default. Nothing applies without your approval.

🔗 geneclaw.ai
📦 github.com/Clawland-AI/Geneclaw

🧵 Here's how it works ↓

---

## Tweet 2 (Architecture)

The evolution pipeline:

Observe → Diagnose → Propose → Gate → Apply

1️⃣ OBSERVE: Every agent interaction is logged as JSONL (tools, errors, messages)
2️⃣ DIAGNOSE: Heuristic analysis + optional LLM identifies failure patterns
3️⃣ PROPOSE: Structured proposals with unified diffs, risk levels, and rollback plans

---

## Tweet 3 (Safety)

4️⃣ GATE: 5 safety checks before any code touches your repo:
  • Path allowlist/denylist
  • Diff size limits
  • Secret scanning
  • Code pattern detection (blocks eval, exec, os.system)

5️⃣ APPLY: Git branch → pre-check → patch → test → auto-rollback on failure

---

## Tweet 4 (Dashboard)

We also built a read-only Streamlit dashboard to audit everything:

📊 KPIs: proposal count, success rate, risk distribution
📈 Timeline: hourly/daily evolution activity
🔍 Audit: inspect any proposal's metadata, files, tests, rollback plan
⚡ Benchmarks: pipeline performance trends

[Attach dashboard screenshot]

---

## Tweet 5 (Try it)

Try it in 5 commands:

```
git clone github.com/Clawland-AI/Geneclaw
pip install -e ".[dev,dashboard]"
nanobot onboard
nanobot geneclaw doctor
nanobot geneclaw evolve --dry-run
```

No LLM key needed — works in heuristic-only mode.

Full docs: geneclaw.ai
Star on GitHub: github.com/Clawland-AI/Geneclaw

---

## Tweet 6 (Question)

The hardest question: when should an AI agent be allowed to modify its own code?

Our answer: never by default. Only after:
✅ Human review
✅ 5-layer safety gate
✅ Git-branched application
✅ Automated test verification
✅ Full audit trail

What would YOU require? Tell us 👇

---

## Posting Notes

- Best time: Tuesday-Thursday, 9-11am ET or 6-8pm ET
- Use images: architecture diagram, dashboard screenshot, terminal GIF
- Engage with replies promptly
- Quote-tweet with individual insights over the next week
