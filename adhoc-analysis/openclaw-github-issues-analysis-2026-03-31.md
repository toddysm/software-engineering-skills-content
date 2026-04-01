# OpenClaw GitHub Issues — Complete Analysis

**Date:** March 31, 2026  
**Repository:** [openclaw/openclaw](https://github.com/openclaw/openclaw)  
**Data Source:** GitHub API via `gh` CLI — all issues (open + closed)  
**Analysis Scope:** 100% of issues (24,697 total)

---

## Executive Summary

OpenClaw is a highly active open-source AI agent framework with **24,697 total issues** (10,170 open, 14,527 closed). The project is experiencing significant growing pains, with the **v2026.3.28 release introducing widespread regressions** — particularly around model failover logic (`LiveSessionModelSwitchError`), channel integration stability, and gateway crashes. Bugs dominate the issue tracker at 57.5%, with feature requests at 23.1%. The community is heavily engaged but visibly frustrated with the regression rate.

---

## Overall Statistics

| Metric | Count |
|--------|------:|
| **Total issues analyzed** | **24,697** |
| **Open issues** | **10,170** |
| **Closed issues** | **14,527** |

---

## Category Breakdown

### All Issues (24,697)

| Category | Count | Percentage |
|----------|------:|----------:|
| **Bug** | 14,199 | 57.5% |
| **Feature Request** | 5,712 | 23.1% |
| **Uncategorized** | 4,663 | 18.9% |
| **Question** | 123 | 0.5% |

### Open Issues (10,170)

| Category | Count | Percentage |
|----------|------:|----------:|
| **Bug** | 5,037 | 49.5% |
| **Feature Request** | 3,029 | 29.8% |
| **Uncategorized** | 2,061 | 20.3% |
| **Question** | 43 | 0.4% |

### Closed Issues (14,527)

| Category | Count | Percentage |
|----------|------:|----------:|
| **Bug** | 9,162 | 63.1% |
| **Feature Request** | 2,683 | 18.5% |
| **Uncategorized** | 2,602 | 17.9% |
| **Question** | 80 | 0.6% |

> **Note:** "Uncategorized" issues lack both labels and clear title keywords to classify. Many are likely bugs or features filed without following the issue template.

---

## Label Statistics (from GitHub)

| Label | Issue Count |
|-------|----------:|
| `bug` | 8,237 |
| `stale` | 4,363 |
| `enhancement` | 2,974 |
| `regression` | 1,420 |
| `bug:behavior` | 1,016 |
| `security` | 219 |
| `r: support` | 183 |
| `bug:crash` | 157 |
| `invalid` | 80 |
| `question` | 50 |
| `tui` | 49 |
| `dedupe:child` | 53 |
| `dedupe:parent` | 46 |
| `maintainer` | 40 |
| `r: spam` | 36 |
| `r: testflight` | 22 |

---

## Theme Analysis — All Issues (24,697)

### Top Themes by Total Issue Count

| Theme | Total | Open | Closed | % of Total |
|-------|------:|-----:|-------:|---------:|
| API/Provider Compatibility | 2,275 | 976 | 1,299 | 9.2% |
| Gateway (runtime/stability) | 2,190 | 971 | 1,219 | 8.9% |
| UI/UX (Control UI, WebChat, TUI, Dashboard) | 2,014 | 968 | 1,046 | 8.2% |
| Session Management | 1,987 | 890 | 1,097 | 8.0% |
| Telegram Integration | 1,758 | 672 | 1,086 | 7.1% |
| Cron/Scheduling | 1,632 | 620 | 1,012 | 6.6% |
| Configuration/Schema | 1,281 | 552 | 729 | 5.2% |
| Authentication/OAuth | 1,108 | 432 | 676 | 4.5% |
| Plugin System | 1,026 | 482 | 544 | 4.2% |
| Discord Integration | 958 | 423 | 535 | 3.9% |
| Installation/Update | 821 | 305 | 516 | 3.3% |
| Multi-Agent/Subagent | 807 | 370 | 437 | 3.3% |
| WhatsApp Integration | 697 | 257 | 440 | 2.8% |
| Memory System | 699 | 292 | 407 | 2.8% |
| Feishu/Lark Integration | 637 | 384 | 253 | 2.6% |
| Security | 633 | 218 | 415 | 2.6% |
| CLI | 593 | 263 | 330 | 2.4% |
| Slack Integration | 556 | 209 | 347 | 2.3% |
| Voice/TTS | 541 | 212 | 329 | 2.2% |
| Browser Automation | 540 | 226 | 314 | 2.2% |
| Docker/Deployment | 479 | 190 | 289 | 1.9% |
| Sandbox/Exec | 478 | 197 | 281 | 1.9% |
| Model Failover/Switching | 463 | 228 | 235 | 1.9% |
| Skills System | 378 | 182 | 196 | 1.5% |
| ACP (Agent Communication Protocol) | 260 | 168 | 92 | 1.1% |
| iMessage/BlueBubbles | 223 | 81 | 142 | 0.9% |
| Performance | 151 | 64 | 87 | 0.6% |
| i18n/Encoding | 132 | 59 | 73 | 0.5% |
| Matrix Integration | 98 | 6 | 92 | 0.4% |
| MS Teams Integration | 94 | 31 | 63 | 0.4% |
| MCP Integration | 90 | 55 | 35 | 0.4% |
| Mattermost Integration | 80 | 33 | 47 | 0.3% |
| Google Chat Integration | 78 | 33 | 45 | 0.3% |
| WeChat/Weixin Integration | 65 | 37 | 28 | 0.3% |

> **Note:** Issues can match multiple themes, so theme totals sum to more than 24,697.

---

## What Bugs Are People Seeing? (Open Bugs by Theme)

| Theme | Open Bugs |
|-------|----------:|
| Gateway (crashes, memory leaks, startup failures) | 652 |
| API/Provider Compatibility | 597 |
| UI/UX (broken controls, desync, rendering) | 527 |
| Session Management (corruption, stuck, leaks) | 430 |
| Telegram (polling stalls, message loss, media failures) | 400 |
| Cron/Scheduling (model override ignored, delivery failures) | 329 |
| Authentication/OAuth (token refresh, scope errors, key leaks) | 285 |
| Configuration/Schema (migration failures, Zod rejects) | 280 |
| Plugin System (loading crashes, hooks not firing) | 275 |
| Discord (gateway crashes on WS 1005, slash command failures) | 245 |
| Feishu/Lark (schema conflicts, streaming failures) | 235 |
| Installation/Update (auto-update crashes, dependency loss) | 210 |
| CLI (command failures, browser CLI broken) | 179 |
| Multi-Agent/Subagent (sessions_spawn failures, stuck sessions) | 155 |
| WhatsApp (creds.json corruption, reconnect loops, outbound failures) | 146 |
| Docker/Deployment (container creation, K8s OOM, systemd issues) | 133 |
| Model Failover/Switching (LiveSessionModelSwitchError loops) | 127 |
| Browser Automation (browser.request not registered, CDP failures) | 125 |
| Memory System (lancedb loading, indexing failures, search empty) | 125 |
| Sandbox/Exec (approval system broken, env vars not passed) | 124 |
| ACP (session binding, cross-agent routing) | 96 |
| Slack (socket mode WS crashes, multi-workspace failures) | 87 |
| Security (SSRF false positives, key leaks, command injection) | 81 |
| Voice/TTS (plugin port conflicts, config ignored, model switch) | 79 |

---

## What Features Are People Requesting? (Open Feature Requests by Theme)

| Theme | Open Features |
|-------|-------------:|
| Session Management (multi-session, cross-channel binding, archival) | 256 |
| UI/UX (media upload, ChatGPT-like interface, dashboard) | 225 |
| API/Provider (new providers, custom inference servers) | 201 |
| Configuration (per-agent overrides, larger file limits) | 168 |
| Cron/Scheduling (multi-channel delivery, structured logging) | 148 |
| Multi-Agent/Subagent (orchestration, task chains, concurrency) | 134 |
| Gateway (graceful restart, session injection, health API) | 122 |
| Plugin System (new hooks, per-agent config, MCP servers) | 117 |
| Telegram (multi-bot, debounce, enhanced ACP) | 113 |
| Memory (consolidation, importance scoring, time decay) | 111 |
| Feishu/Lark (video support, feishu-sheet skill, voice) | 85 |
| Skills System (conditional activation, frontmatter validation) | 81 |
| Voice/TTS (per-agent voice, new TTS providers) | 79 |
| Security (RBAC, PII redaction, outbound policy, secret mgmt) | 76 |
| Authentication/OAuth (health monitoring, trustable proxy) | 74 |
| Discord (threads inheritance, voice wake word, delivery queue) | 73 |
| Slack (inline buttons, rich text, configurable reconnect) | 60 |
| Browser Automation (viewport config, profile import) | 58 |
| WhatsApp (quoted reply support, QR scan, pairing notify) | 54 |
| Model Failover/Switching (circuit breaker, user-visible notice) | 46 |

---

## What Questions Are People Asking?

The 123 question-type issues primarily include:
- **iOS TestFlight access requests** (22 labeled `r: testflight`)
- **Support requests** (183 labeled `r: support`) — mostly setup/configuration help
- **Build/install guidance** — users trying to build from source
- **Community showcases** ("Show & Tell" posts sharing integrations)
- **General "how do I..." questions** about specific features

---

## Channel Integration Deep Dive

| Channel | Total Issues | Open | Closed | Top Problems |
|---------|------------:|-----:|-------:|-------------|
| **Telegram** | 1,758 | 672 | 1,086 | Polling stalls, SSRF blocking media downloads, forum topic routing, message loss on restart, DM failures on Windows/macOS |
| **Discord** | 958 | 423 | 535 | Gateway crashes on WebSocket code 1005, stale-socket health monitor false positives, slash commands failing, voice silence, message ordering |
| **WhatsApp** | 697 | 257 | 440 | creds.json corruption on reconnect, outbound "No Active Listener" failure, reconnect loops causing V8 heap crash, group policy regression |
| **Feishu/Lark** | 637 | 384 | 253 | Schema conflicts with core, streaming card HTTP 400, multi-account WebSocket failures, footer config rejected, duplicate tool registrations |
| **Slack** | 556 | 209 | 347 | Socket Mode WebSocket crashes (code 1005), event loop starvation, stale-socket reconnect message loss, multi-workspace inbound failures |
| **iMessage/BlueBubbles** | 223 | 81 | 142 | Config round-trip bugs (Zod defaults), reply tags visible in messages, inbound drops during activity |
| **Matrix** | 98 | 6 | 92 | Device verification failures, message replay after restart, room ID case sensitivity crashes |
| **MS Teams** | 94 | 31 | 63 | Thread replies routing wrong, path-to-regexp crash, typing indicator duplication |
| **MCP** | 90 | 55 | 35 | Tool result format incompatibilities, elicitation support, timeout failures |
| **Mattermost** | 80 | 33 | 47 | Config validation breaking on upgrade, RootId fallback, requireMention per-thread |
| **Google Chat** | 78 | 33 | 45 | JWT verification failures, space/group messages silently ignored, webhook 401 errors |
| **WeChat/Weixin** | 65 | 37 | 28 | Daily token expiry, message duplication (hundreds of times), cron delivery failures |

---

## Provider/Model Mention Analysis

How often specific providers or models are mentioned in issue titles:

| Provider | Total Issues | Open |
|----------|------------:|-----:|
| **Anthropic/Claude** | 499 | 184 |
| **OpenAI/GPT** | 477 | 212 |
| **Ollama** | 243 | 74 |
| **Gemini (Google)** | 238 | 103 |
| **Codex** | 231 | 127 |
| **Kimi** | 164 | 47 |
| **MiniMax** | 125 | 52 |
| **OpenRouter** | 110 | 49 |
| **xAI/Grok** | 61 | 20 |
| **Bedrock (AWS)** | 53 | 29 |
| **Moonshot** | 51 | 15 |
| **DeepSeek** | 32 | 13 |
| **Qwen** | 27 | 10 |
| **Mistral** | 22 | 13 |
| **Perplexity** | 22 | 9 |
| **Groq** | 16 | 6 |

---

## v2026.3.28 Regression Analysis

The v2026.3.28 release is a major pain point:

| Metric | Count |
|--------|------:|
| Issues explicitly mentioning v2026.3.28 in title | **81** |
| ...of which still open | **68** (84% unresolved) |
| Issues mentioning `LiveSessionModelSwitch` | **43** |
| ...of which still open | **31** (72% unresolved) |

### Key v2026.3.28 Regressions
- **LiveSessionModelSwitchError** blocks all model failover, creating infinite retry loops
- **browser.request** method not registered — browser automation completely broken
- **Config schema** rejects previously valid configs (enrichGroupParticipantsFromContacts, messages.tts.edge)
- **operator.write scope enforcement** breaks /v1 API clients
- **Plugin loading** failures and crash loops
- **Discord/Telegram** channels fail to initialize on startup
- **memory-lancedb** can't load (missing dist/package.json)
- **Auto-update** is non-atomic, causing config/plugin version mismatches

---

## Key Findings

### 1. Gateway Is the #1 Bug Surface (652 open bugs)
The gateway runtime has the most bug reports of any component. Issues include crash loops from uncaught exceptions (especially Discord WebSocket code 1005), memory leaks causing OOM after extended uptime, event loop freezes, and zombie processes preventing restarts.

### 2. API/Provider Compatibility Is the #2 Pain Point (597 open bugs)
Provider-specific API format issues (Anthropic, Gemini, Bedrock, Kimi, MiniMax), tool call serialization failures, and scope enforcement regressions are widespread. The rapid growth in supported providers without sufficient integration testing is evident.

### 3. Channel Integrations Account for 5,334 Total Issues
When summing all channel-related issues (Telegram, Discord, WhatsApp, Feishu, Slack, etc.), they represent **21.6% of all issues**. Telegram alone has 1,758 issues. The quality of integration varies significantly across platforms.

### 4. Cron/Scheduling Is Broadly Broken (620 open)
The combination of `payload.model` being silently overridden by LiveSessionModelSwitchError, CLI validation failures ("job must be object"), and delivery issues across channels makes the cron system unreliable.

### 5. Session Management Is Fragile (890 open)
Session state corruption, subagent lifecycle issues, performance degradation at scale, and cross-session context leakage represent fundamental architectural concerns.

### 6. v2026.3.28 Broke 68+ Things That Haven't Been Fixed
With 84% of v2026.3.28-mentioning issues still open, this release represents a trust crisis with users. The `regression` label has 1,420 issues — a staggeringly high number.

### 7. Feature Requests Are Ambitious
The community wants multi-agent orchestration (134 open), ChatGPT-like UI (225 open), persistent memory with time decay (111 open), and expanded provider/channel support. These requests show a mature user base pushing the platform toward production-grade capabilities.

### 8. 1,420 Regressions — Release Quality Concern
The `regression` label on 1,420 issues signals a fundamental release quality problem. The project would benefit from better regression testing, staged rollouts, and a more conservative release cadence.

---

## Methodology

- **Data Collection:** `gh issue list --repo openclaw/openclaw --state all --limit 20000 --json number,title,labels,state` via authenticated GitHub CLI
- **Category Classification:** Label-based first (bug, enhancement, question, regression), then title pattern matching using regex for unlabeled issues
- **Theme Classification:** Regex-based keyword matching against issue titles and labels, with 34 distinct theme categories. Issues can match multiple themes.
- **Limitations:** 4,663 issues (18.9%) could not be categorized into Bug/Feature/Question due to lack of labels and ambiguous titles. Theme classification is title-based and may miss context only present in issue bodies.
