# Components Guide — OpenClaw

**Date:** 2026-03-18

---

## Component Architecture

OpenClaw is organized as a pnpm monorepo with clearly separated concerns. This guide explains how the major components relate and interact.

---

## Core Engine (`src/`)

The core engine contains the runtime logic.

### Gateway (`src/gateway/`)
The **central nervous system** of OpenClaw. A WebSocket server that:
- Accepts connections from CLI, mobile apps, web UI, and webhooks
- Manages channel lifecycle (connect, disconnect, health)
- Dispatches inbound messages to agents
- Routes outbound replies to channels
- Provides RPC methods for all system operations

**Key files:**
| File | Purpose |
|------|---------|
| `server.impl.ts` | Gateway bootstrap & lifecycle management |
| `server.ts` | Main handler exports |
| `server-channels.ts` | Inbound message dispatch |
| `server-methods/` | RPC method implementations |
| `protocol/` | WebSocket protocol definitions |
| `auth.ts` | Token & RBAC authentication |

**Depends on:** agents, channels, config, plugins, sessions, routing

---

### Agents (`src/agents/`)
The **AI orchestration layer**. Manages LLM interactions, tool execution, and streaming.

**Key files:**
| File | Purpose |
|------|---------|
| `pi-embedded-runner.ts` | Core agent execution loop |
| `pi-embedded-subscribe.ts` | Block-level streaming handlers |
| `pi-tools.ts` | Tool catalog (browser, system.run, etc.) |
| `bash-tools.ts` | system.run approval & execution |
| `subagent-*.ts` | Multi-agent spawn & control |
| `model-*.ts` | Model selection & failover |
| `skills/` | Skill discovery & loading |

**Depends on:** providers, config, sessions, plugins, tools

---

### Channels (`src/channels/`)
The **messaging abstraction layer**. Provides a unified interface for 25+ platforms.

**Key files:**
| File | Purpose |
|------|---------|
| `session.ts` | Session model (conversation tracking) |
| `registry.ts` | Channel plugin registry |
| `plugins/types.plugin.ts` | ChannelPlugin interface |
| `plugins/binding-types.ts` | Conversation binding types |
| `run-state-machine.ts` | Inbound processing state machine |
| `routing/` | Session routing logic |
| `transport/` | Outbound delivery |
| `allowlists/` | User allowlist matching |

**Depends on:** config, sessions, plugins

---

### Config (`src/config/`)
**Configuration management** — loads, validates, and serves the YAML config.

**Key files:**
| File | Purpose |
|------|---------|
| `config.ts` | YAML/JSON config loader |
| `types.ts` | Type definitions for all config |
| `zod-schema.*.ts` | Zod validation schemas |
| `sessions.ts` | Session store model |
| `legacy.ts` | Migration from old config formats |
| `schema.hints.ts` | Config help text & docs |

**Depends on:** types

---

### Plugins (`src/plugins/`)
The **plugin framework** — manages loading, lifecycle, and hook dispatch for extensions.

**Key files:**
| File | Purpose |
|------|---------|
| `loader.ts` | Dynamic plugin loading |
| `registry.ts` | Plugin registry |
| `hooks.ts` | Hook dispatcher |
| `manifest.ts` | Plugin manifest parsing |
| `runtime/` | Plugin runtime environment |
| `provider-*.ts` | Provider plugin management |

**Depends on:** config, types

---

### Providers (`src/providers/`)
**LLM provider integration** layer.

**Key files:**
| File | Purpose |
|------|---------|
| `provider-catalog.ts` | Model discovery & catalog |
| `provider-auth.ts` | OAuth/API-key setup |
| `provider-runtime.ts` | Provider RPC execution |

**Depends on:** plugins, config

---

### CLI (`src/cli/`)
**Command-line interface** with 80+ subcommands.

**Key files:**
| File | Purpose |
|------|---------|
| `run-main.ts` | CLI entrypoint |
| `program.ts` | Command builder |
| `route.ts` | Command routing |
| `commands/` | Individual command implementations |

**Depends on:** gateway, config, agents

---

## Extension Ecosystem (`extensions/`)

76 extensions organized by type:

### Channel Extensions
| Extension | Platform | SDK |
|-----------|----------|-----|
| `discord` | Discord | discord.js |
| `slack` | Slack | @slack/bolt |
| `telegram` | Telegram | grammY |
| `whatsapp` | WhatsApp | Baileys |
| `signal` | Signal | signal-cli subprocess |
| `imessage` | iMessage | BlueBubbles HTTP |
| `matrix` | Matrix | matrix-sdk |
| `msteams` | Microsoft Teams | Bot Framework |
| `googlechat` | Google Chat | Google API |
| `mattermost` | Mattermost | API client |
| `feishu` | Feishu/Lark | API client |
| `line` | LINE | Messaging API |
| `irc` | IRC | IRC client |
| `nostr` | Nostr | Protocol lib |
| `twitch` | Twitch | Chat API |

### Provider Extensions
| Extension | Provider | Models |
|-----------|----------|--------|
| `openai` | OpenAI | GPT-4, GPT-4o, o1, etc. |
| `anthropic` | Anthropic | Claude 3/3.5/4 |
| `google` | Google | Gemini Pro/Ultra |
| `ollama` | Ollama (local) | Llama, Mistral, etc. |
| `amazon-bedrock` | AWS Bedrock | Multiple providers |
| `mistral` | Mistral AI | Mistral models |
| `together` | Together AI | Open models |
| `openrouter` | OpenRouter | Multi-provider |
| `vllm` | vLLM (local) | Self-hosted models |
| `sglang` | SGLang (local) | Self-hosted models |
| `xai` | xAI | Grok models |
| `perplexity` | Perplexity | Sonar models |
| `nvidia` | NVIDIA | NIM models |

### Tool/Feature Extensions
| Extension | Purpose |
|-----------|---------|
| `memory-lancedb` | Vector memory with LanceDB |
| `memory-core` | Core memory plugin framework |
| `voice-call` | Voice calling support |
| `talk-voice` | Voice interaction mode |
| `diffs` | Code diff visualization |
| `diagnostics-otel` | OpenTelemetry diagnostics |
| `device-pair` | Device pairing protocol |
| `open-prose` | Writing assistance |
| `firecrawl` | Web crawling |

---

## Skills Ecosystem (`skills/`)

52 bundled skills providing domain-specific tools:

| Category | Skills |
|----------|--------|
| **Productivity** | apple-notes, apple-reminders, things-mac, obsidian, notion, bear-notes, trello, canvas |
| **Development** | github, gh-issues, coding-agent, skill-creator |
| **Communication** | slack, discord, bluebubbles, imsg, wacli |
| **Media** | openai-image-gen, video-frames, gifgrep, peekaboo, camsnap, songsee |
| **Smart Home** | openhue, sonoscli, node-connect |
| **Voice** | openai-whisper, openai-whisper-api, sherpa-onnx-tts, voice-call |
| **Utilities** | weather, xurl, healthcheck, oracle, session-logs, model-usage, summarize |
| **System** | tmux, blucli, goplaces, himalaya, ordercli, mcporter |

---

## Mobile & Desktop Apps (`apps/`, `Swabble/`)

### iOS App (`apps/ios/`)
- **Technology:** Swift + SwiftUI
- **Connection:** WebSocket to local/remote Gateway
- **Features:** Canvas display, voice wake, talk mode, camera integration, screen recording

### Android App (`apps/android/`)
- **Technology:** Kotlin
- **Connection:** WebSocket to Gateway
- **Features:** Setup codes (Connect tab), chat sessions, voice tab, device integration (location, notifications, SMS, contacts)

### macOS App (`apps/macos/`)
- **Technology:** Swift (menu bar + standalone)
- **Connection:** Direct WebSocket
- **Features:** Menu bar control, quick actions

### Swabble Framework (`Swabble/`)
- **Shared Swift library** for iOS/macOS
- `SwabbleCore` — networking layer, model definitions, gateway client
- `SwabbleKit` — reusable UI kit (canvas, chat views, controls)

---

## Web Control UI (`ui/`)
- **Technology:** React + TypeScript
- **Purpose:** Browser-based dashboard for managing agents, channels, sessions
- Connects to Gateway via auth token + WebSocket

---

## Component Interaction Summary

```
                    ┌─────────┐
                    │   CLI   │
                    └────┬────┘
                         │ RPC
┌──────────┐     ┌───────▼───────┐     ┌───────────┐
│Extensions│◄────┤   Gateway     ├────►│   Agents  │
│(Channels)│     │ (Control Plane)│     │ (Pi Runtime)│
└──────────┘     └───┬───┬───┬───┘     └─────┬─────┘
                     │   │   │               │
              ┌──────┘   │   └──────┐        │
              ▼          ▼          ▼        ▼
         ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
         │Sessions│ │ Config │ │Plugins │ │Providers│
         └────────┘ └────────┘ └────────┘ └────────┘
                                               │
                                    ┌──────────┘
                                    ▼
                              ┌───────────┐
                              │LLM APIs   │
                              │(External) │
                              └───────────┘
```
