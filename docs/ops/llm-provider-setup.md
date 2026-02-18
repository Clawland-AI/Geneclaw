# LLM Provider Setup — Secure Configuration Guide

> How to configure an LLM provider for Geneclaw without exposing API keys.

**Rule: API keys must NEVER be committed to the repository.**

---

## 1. Supported Providers

| Provider | Model Example | Get API Key |
|----------|---------------|-------------|
| **OpenRouter** (recommended) | `openrouter/anthropic/claude-opus-4-5` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **Anthropic** | `anthropic/claude-opus-4-5` | [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI** | `openai/gpt-4o` | [platform.openai.com](https://platform.openai.com) |
| **DeepSeek** | `deepseek/deepseek-chat` | [platform.deepseek.com](https://platform.deepseek.com) |
| **Gemini** | `gemini/gemini-2.0-flash` | [aistudio.google.com](https://aistudio.google.com) |

OpenRouter is recommended for global availability — one key provides access to all major models.

---

## 2. Configuration Method: Environment Variable + Config File

### Step 1: Export your API key as an environment variable

**Linux / macOS:**
```bash
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
```

**Windows (cmd):**
```cmd
set OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

To persist across sessions, add the export to your shell profile (`~/.bashrc`, `~/.zshrc`, or PowerShell `$PROFILE`).

### Step 2: Set the API key in config (one-time)

Edit `~/.nanobot/config.json` and set the `apiKey` field for your provider:

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-your-key-here"
    }
  },
  "agents": {
    "defaults": {
      "model": "openrouter/anthropic/claude-opus-4-5"
    }
  }
}
```

> **Important:** `~/.nanobot/config.json` lives outside the repository
> and is listed on the geneclaw denylist. It will never be committed.

### Step 3: Verify

```bash
nanobot status
```

You should see the provider listed with a green checkmark. If the key is
invalid, the status command will report an error.

---

## 3. Security Checklist

- [ ] API key is set in `~/.nanobot/config.json` (outside the repo)
- [ ] `config.json` is on the geneclaw denylist (`denylistPaths`)
- [ ] `.env` is in `.gitignore`
- [ ] `geneclaw.redact_enabled = true` in config
- [ ] Run `nanobot geneclaw doctor` — verify "redact_enabled" shows green
- [ ] Never paste API keys into chat messages or agent prompts
- [ ] Never include API keys in commit messages or PR descriptions

---

## 4. How Redaction Protects You

Even if an API key accidentally appears in an agent conversation or tool
output, Geneclaw's redaction layer will mask it before writing to logs:

```
Input:  api_key="sk-or-v1-abc123def456"
Output: api_key="[REDACTED]"
```

Redaction patterns cover:
- `api_key`, `api_secret`, `token`, `secret`, `password`, `authorization`
- Bearer tokens (`Bearer sk-...`)
- PEM private keys (`-----BEGIN ... PRIVATE KEY-----`)

---

## 5. Provider-Specific Notes

### OpenRouter
- Model format: `openrouter/<provider>/<model>` or just `<provider>/<model>`
- Free tier available for some models
- Dashboard: https://openrouter.ai/activity

### Anthropic (Direct)
- Model format: `anthropic/claude-opus-4-5`
- Requires billing setup at console.anthropic.com
- Rate limits may apply depending on plan

### DeepSeek
- Model format: `deepseek/deepseek-chat`
- Cost-effective for large context windows
- API base: `https://api.deepseek.com`

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: No API key configured` | Key not set in config | Set `providers.<name>.apiKey` in `~/.nanobot/config.json` |
| `No LLM provider — heuristic-only mode` | Key missing; evolve/autopilot falls back | Set a valid API key (Section 2) |
| `401 Unauthorized` | Invalid or expired key | Regenerate key at provider dashboard |
| `429 Rate Limited` | Too many requests | Wait and retry; or upgrade plan |
| Redaction not working | `redact_enabled` is false | Set `geneclaw.redactEnabled: true` in config |

---

## 7. Next: Generate Your First Real Proposal

Once your provider is configured:

```bash
nanobot geneclaw doctor          # verify everything is green
nanobot agent -m "Hello"         # generate run events
nanobot geneclaw evolve --dry-run  # generate a real proposal
```

See [First Real Proposal Guide](first-real-proposal.md) for the complete walkthrough.
