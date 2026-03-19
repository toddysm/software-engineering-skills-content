# Architecture Overview — OpenClaw

**Date:** 2026-03-18
**Analyst:** codebase-architecture-analyst
**Repository:** https://github.com/openclaw/openclaw.git
**Language Breakdown:** TypeScript (7,085 files), Swift (605), Kotlin (118), Shell (71), JavaScript (69), Python (10)
**Total Source Files Analyzed:** 7,838

---

## Executive Summary

OpenClaw is a **personal AI assistant platform** designed to run on your own devices. It provides a multi-channel, multi-agent system that connects 25+ messaging platforms (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, Matrix, IRC, LINE, etc.) to LLM providers (OpenAI/ChatGPT, Anthropic/Claude, Google/Gemini, Ollama/local models, and 20+ more) through a local WebSocket gateway.

The system follows a **plugin-oriented, event-driven architecture** with clear separation between:
1. **Messaging channel adapters** (inbound/outbound message handling)
2. **AI agent runtime** (LLM orchestration, tool execution, streaming)
3. **Gateway control plane** (WebSocket RPC, session management, routing)
4. **Extension/plugin ecosystem** (channel integrations, provider integrations, skills)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         Messaging Channels (25+ platforms)                   │
│  WhatsApp · Telegram · Slack · Discord · Signal · iMessage   │
│  Matrix · Teams · Google Chat · Feishu · LINE · IRC · etc    │
└─────────────────┬───────────────────────────────────────────┘
                  │ Inbound messages (normalized)
┌─────────────────▼───────────────────────────────────────────┐
│       Gateway Control Plane — ws://127.0.0.1:18789          │
│  ┌────────────────┬─────────────┬──────────────┐            │
│  │ Session Mgmt   │ Channel Mgr │ Config/Auth  │            │
│  │ Routing Engine │ Tool Catalog│ Model Hot-swap│           │
│  └────────────────┴─────────────┴──────────────┘            │
└─────────────────┬───────────────────────────────────────────┘
                  │ Agent dispatch
        ┌─────────┼─────────┐
        │         │         │
┌───────▼──┐ ┌───▼────┐ ┌──▼──────┐
│ Pi Agent │ │  CLI   │ │ Control │
│ (RPC)    │ │Commands│ │ UI/Web  │
└─────┬────┘ └────────┘ └─────────┘
      │ API calls
┌─────▼────────────────────────────────────────────────────────┐
│         LLM Provider Layer (20+ providers)                    │
│  Anthropic · OpenAI · Google · Ollama · Bedrock · Mistral     │
│  Together · OpenRouter · vLLM · SGLang · xAI · Perplexity    │
└──────────────────────────────────────────────────────────────┘
```

---

## Monorepo Structure

OpenClaw uses a **pnpm workspace monorepo** with the following major areas:

| Directory | Purpose | Approx. Files |
|-----------|---------|---------------|
| `src/` | Core engine (gateway, agents, channels, plugins, CLI) | ~3,500 TS |
| `extensions/` | 76 pluggable integrations (channels, providers, tools) | ~2,500 TS |
| `skills/` | 52 bundled agent skills (GitHub, Slack, 1Password, etc.) | ~600 |
| `Swabble/` | Swift core library for iOS/macOS apps | ~300 Swift |
| `apps/` | Mobile/desktop apps (iOS, Android, macOS) | ~400 |
| `ui/` | Web-based control dashboard | ~100 TS/TSX |
| `docs/` | Mintlify documentation site | ~200 MD |
| `scripts/` | Build, deployment, and dev automation | ~150 |
| `test/` | Integration/E2E test infrastructure | ~100 |
| `packages/` | Internal workspace packages (clawdbot, moltbot) | ~50 |

---

## Core Design Patterns

### 1. Plugin System (Two-Tier Architecture)

OpenClaw's extensibility is built on a two-tier plugin architecture:

**Tier 1 — Channel Plugins** (`extensions/*/src/channel.ts`):
- Implement the `ChannelPlugin` interface from `src/channels/plugins/types.plugin.ts`
- Handle: setup wizard, OAuth, send/receive messages, config schema
- Examples: Discord (discord.js), Slack (@slack/bolt), Telegram (grammY), WhatsApp (Baileys)

**Tier 2 — Provider Plugins** (`extensions/*/src/`):
- Implement the `ProviderPlugin` interface from `src/plugins/types.ts`
- Handle: model catalog, auth flow, streaming chat, tool/function-calling support
- Examples: OpenAI, Anthropic, Google Gemini, Ollama

**Plugin Discovery & Loading:**
- Manifest declared in `package.json` → `openclaw.extensions` array
- Auto-loaded from `extensions/*/index.ts` at gateway boot
- Dynamic loading via `src/plugins/loader.ts`
- Hook system (`src/hooks/`) allows lifecycle callbacks (before-agent-start, after-tool-call, on-error)

### 2. Session & Routing Model

Every conversation is tracked as a **Session** (`src/channels/session.ts`):
- Session key format: `"main"` or `"dm:user:@alice"`
- Persists conversation history, last channel, target ID, thread ID
- Supports multi-account routing

**Routing flow:**
1. Channel plugin receives inbound message → normalizes to `ChannelMessage`
2. Gateway resolves session key → loads/creates session
3. Agent selected via route binding (`src/routing/`)
4. Agent executes with full history → streams response
5. Reply routed back through channel transport layer

### 3. Pi Agent Runtime (Embedded RPC)

The core AI agent orchestrator (`src/agents/pi-embedded-*.ts`):
- Loads model configuration & tool permissions
- Streams responses block-by-block (text, tool-use, tool-result)
- Executes tool calls synchronously within the conversation loop
- Supports multi-agent spawning via `subagent-*.ts`
- Context management with automatic history pruning
- Optional Docker sandbox for `system.run` tool

### 4. Gateway WebSocket Control Plane

The gateway (`src/gateway/server.impl.ts`) provides:
- WebSocket RPC at `ws://127.0.0.1:18789`
- Methods: `session.send`, `channels.status`, `models.set`, `agent.run`, etc.
- Auth modes: none (loopback-only), token, OAuth (Tailscale/remote)
- Connected by: CLI, mobile apps, web UI, external webhooks

### 5. Configuration System

YAML-based configuration (`~/.openclaw/config.yaml`):
- Validated by Zod schemas (`src/config/zod-schema.*.ts`)
- Supports env var interpolation (`$ANTHROPIC_API_KEY`)
- Auto-migration from legacy formats (`src/config/legacy.ts`)
- Per-agent, per-channel, per-model granular configuration

---

## Data Flow: Message Lifecycle

```
User sends "Hello" on Slack
    │
    ▼
[1. SlackPlugin.receiveInbound]
    ├─ Fetch user metadata from Slack API
    ├─ Normalize to ChannelMessage { from, text, channel }
    └─ Emit to Gateway
    │
    ▼
[2. Gateway.onInbound] (src/gateway/server-channels.ts)
    ├─ Validate allowlist (user authorized?)
    ├─ Apply pairing policy (new sender approval flow)
    ├─ Record inbound session in session store
    └─ Select agent for route
    │
    ▼
[3. runEmbeddedPiAgent] (src/agents/pi-embedded-runner.ts)
    ├─ Load session history (capped by historyLimit)
    ├─ Build system prompt (identity + tools + skills)
    ├─ Call LLM API (Anthropic/OpenAI/fallback chain)
    ├─ Stream response tokens
    ├─ Execute tool calls (browser, system.run, etc.)
    └─ Save final result to session store
    │
    ▼
[4. Channel Reply] (src/channels/transport/)
    ├─ Route to original channel (or cross-channel replyTo)
    ├─ Apply media transformation (resize, caption)
    └─ SlackPlugin.sendMessage → Slack API
```

---

## Tool & Skill System

**Tools** = functions agents can call during conversations:
- **Built-in:** browser automation, system.run (shell), canvas, image generation, cron, camera/location
- **Plugin-provided:** Channel actions (Discord/Slack), memory search, MCP tools
- **Skills:** 52 bundled domain-specific tools (GitHub, 1Password, Apple Notes, weather, etc.)

**Tool execution sandboxing:**
- `system.run` requires explicit user approval
- Optional Docker isolation for untrusted code
- Tool allowlists/denylists per agent configuration

---

## Mobile & Desktop Architecture

| Platform | Location | Technology | Connection |
|----------|----------|------------|------------|
| **iOS** | `apps/ios/` | Swift + SwiftUI | WebSocket to Gateway |
| **macOS** | `apps/macos/`, `Swabble/` | Swift (menu bar app) | WebSocket to Gateway |
| **Android** | `apps/android/` | Kotlin | WebSocket to Gateway |
| **Web** | `ui/` | React/TypeScript | HTTP + WebSocket |

**Swabble** (`Swabble/Sources/`) is a shared Swift framework:
- `SwabbleCore` — networking, models, gateway client
- `SwabbleKit` — UI components (canvas, chat, controls)

---

## Testing Strategy

- **Framework:** Vitest with V8 coverage (70% threshold)
- **Unit tests:** `*.test.ts` (colocated with source)
- **Integration tests:** `*.integration.test.ts` (full gateway harness)
- **E2E tests:** `*.e2e.test.ts` (Docker, external services)
- **Live tests:** `*.live.test.ts` (real API keys, gated by env var)

---

## Deployment Options

| Method | Config | Description |
|--------|--------|-------------|
| **npm global** | `npm install -g openclaw` | CLI + daemon |
| **Docker** | `docker-compose.yml`, `Dockerfile` | Containerized gateway |
| **Fly.io** | `fly.toml` | Production cloud hosting |
| **systemd/launchd** | `openclaw onboard --install-daemon` | System service |
| **Nix** | Community-contributed flake | Declarative installation |

---

## Architectural Concerns

1. **Circular dependency detected:** `ui/src/ui/app-settings.ts` ↔ `ui/src/ui/app-chat.ts`
2. **1,505 files** flagged with high complexity scores
3. **Low documentation coverage** (~7% of files have inline documentation)
4. **Large codebase surface area:** 7,838 source files across 6 languages makes comprehensive testing challenging
5. **Extension ecosystem isolation:** 76 extensions must be kept compatible across updates

---

## Key Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| npm binary | `openclaw.mjs` | Node.js launcher |
| CLI boot | `src/index.ts` | Main CLI entrypoint |
| CLI router | `src/cli/run-main.ts` | Command parsing & dispatch |
| Gateway start | `src/gateway/server.impl.ts` | WebSocket server boot |
| Agent execution | `src/agents/pi-embedded-runner.ts` | LLM conversation loop |
| Channel inbound | `src/gateway/server-channels.ts` | Inbound message dispatch |
| Config loading | `src/config/config.ts` | YAML parsing & validation |
| Plugin loading | `src/plugins/loader.ts` | Dynamic extension discovery |
