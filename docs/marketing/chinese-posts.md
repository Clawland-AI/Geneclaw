# 中文推广文案

---

## 知乎 / 微信公众号 — 深度文章

### 标题

开源：Geneclaw——一个能"安全自进化"的 AI Agent 框架

### 正文

> TL;DR: 我们开源了 Geneclaw，一个 AI Agent 自进化框架。Agent 能观测自身运行时故障，诊断根因，生成受约束的代码补丁，并在 5 层安全门禁后自动应用。一切默认 dry-run，未经人工审批绝不落盘。

**为什么需要"自进化"？**

现有的 AI Agent 框架（AutoGPT、CrewAI、MetaGPT 等）让 agent 执行用户任务，但当 agent 自身的工具调用出错、异常反复发生时，还是需要人来诊断和修复。

如果 agent 能"看见"自己的问题，并在安全约束下自我修复呢？

**Geneclaw 的进化闭环：**

```
观测 → 诊断 → 提案 → 门禁 → 应用
```

1. **观测（Observe）**：每次 agent 交互自动记录为 JSONL（消息、工具调用、异常、响应时间）
2. **诊断（Diagnose）**：启发式分析 + 可选 LLM 辅助识别失败模式
3. **提案（Propose）**：生成结构化 JSON 提案（含 unified diff、风险等级、回滚方案）
4. **门禁（Gate）**：5 层安全校验
   - 路径白名单/黑名单
   - Diff 行数上限
   - 密钥扫描（API key、token、PEM）
   - 危险代码模式检测（eval、exec、os.system）
5. **应用（Apply）**：Git 分支隔离 → `git apply --check` → 测试 → 失败自动回滚

**安全是第一设计约束，不是事后补丁。**

**不需要 LLM 也能工作**——内置启发式诊断引擎，在没有 API key 的环境下依然能运行完整流水线。

**可视化审计**——内置 Streamlit Dashboard，支持 KPI 概览、时间线、提案审计、性能基准四个页面。

**渐进式信任模型：**

| 阶段 | 允许修改的目录 | 条件 |
|------|---------------|------|
| 启动期 | `geneclaw/`, `docs/` | 第 1 天 |
| 扩展期 | + `tests/` | 审核 5+ 提案后 |
| 完整期 | + `nanobot/` | 审核 20+ 提案后 |

**Quick Start:**

```bash
git clone https://github.com/Clawland-AI/Geneclaw.git
cd Geneclaw && pip install -e ".[dev,dashboard]"
nanobot onboard
nanobot geneclaw doctor
nanobot geneclaw evolve --dry-run
nanobot geneclaw dashboard
```

- 官网：[geneclaw.ai](https://geneclaw.ai)
- GitHub：[Clawland-AI/Geneclaw](https://github.com/Clawland-AI/Geneclaw)
- 协议规范：[GEP-v0.md](https://github.com/Clawland-AI/Geneclaw/blob/master/docs/specs/GEP-v0.md)

欢迎 Star、Issue、PR，也欢迎讨论：**AI 系统应该在什么条件下被允许修改自己的代码？**

---

## 微博 / 即刻 — 短文案

🧬 开源了 Geneclaw——一个能"安全自进化"的 AI Agent 框架。

Agent 能自己发现 bug、诊断原因、生成补丁、通过 5 层安全门禁后自动修复。

关键：一切默认 dry-run，不审批不应用。

→ 观测 → 诊断 → 提案 → 门禁 → 应用

不需要 API key 也能跑（启发式模式）。内置 Streamlit 审计 Dashboard。123 个测试全通过。

🔗 geneclaw.ai
📦 github.com/Clawland-AI/Geneclaw

---

## V2EX — 帖子

### 标题

[开源] Geneclaw：让 AI Agent 安全地自我进化

### 内容

做了一个开源项目，在 nanobot（港大的轻量 AI agent 框架）上加了自进化引擎。

核心理念：Agent 不只是执行任务，还能持续观测自身故障、生成修复提案、在安全约束下自我改进。

安全模型是核心卖点：
- 默认 dry-run，不批准不应用
- 5 层 Gatekeeper（白名单、黑名单、diff 限制、密钥扫描、危险代码检测）
- Git 分支隔离 + 测试 + 失败自动回滚
- 全链路 JSONL 审计日志 + Streamlit Dashboard

不需要 LLM API key 也能工作（启发式模式）。

官网：geneclaw.ai
GitHub：github.com/Clawland-AI/Geneclaw

欢迎交流！
