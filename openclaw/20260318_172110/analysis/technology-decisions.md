# Technology Decisions — OpenClaw

**Date:** 2026-03-18

---

## Language & Runtime Choices

### TypeScript (Primary — 7,085 files)
**Why:** TypeScript provides type safety for a large, multi-contributor codebase while maintaining JavaScript ecosystem compatibility. The project uses **strict mode** TypeScript with ESM modules.

**Trade-offs:** The team chose TypeScript over alternatives like Go or Rust because:
- Node.js has the richest ecosystem of messaging platform SDKs (discord.js, grammY, @slack/bolt, Baileys, etc.)
- Streaming/async patterns map well to Node.js event loop
- Easier contribution from web developers
- Shared language with the web UI

**Runtime:** Node.js ≥22 (required for native ESM, fetch, WebSocket APIs). Bun supported as optional faster runtime for dev loops.

### Swift (605 files — iOS/macOS)
**Why:** Native Apple platform language required for:
- SwiftUI for modern iOS/macOS UI
- System integration (camera, notifications, shortcuts)
- Menu bar app functionality
- WebSocket client with system-level networking

### Kotlin (118 files — Android)
**Why:** Standard Android development language. Required for:
- Native Android UI
- Device integration (location, SMS, contacts, notifications)
- Background service for persistent WebSocket connection

---

## Architecture Decisions

### WebSocket Gateway (vs. REST API)
**Decision:** Use WebSocket as the primary communication protocol.

**Reasoning:**
- Bi-directional real-time streaming is essential for LLM token-by-token output
- Persistent connections reduce latency for mobile apps
- Natural fit for event-driven message routing
- Supports multiple concurrent sessions efficiently

**Port:** `ws://127.0.0.1:18789` — chosen to avoid conflicts with common services

### Plugin Architecture (vs. Monolith)
**Decision:** Two-tier plugin system for channels and providers.

**Reasoning:**
- 76 extensions would bloat the core if embedded
- Each channel SDK has different dependencies and lifecycle
- Provider APIs change independently — plugin isolation prevents cascade failures
- Community can contribute new extensions without modifying core
- Extensions loaded dynamically at gateway boot

### YAML Configuration (vs. JSON/TOML/Database)
**Decision:** YAML with Zod validation for configuration.

**Reasoning:**
- Human-readable and editable (config is user-facing)
- Supports comments for documentation
- Environment variable interpolation (`$API_KEY`)
- Zod schemas provide runtime validation with helpful error messages
- Migration system handles format evolution

### Embedded Agent Runtime (vs. External Agent Service)
**Decision:** Run the Pi agent embedded in the Gateway process.

**Reasoning:**
- Eliminates inter-process communication latency
- Simplifies deployment (single process)
- Tool execution shares the same runtime (filesystem, network)
- Streaming is native (no serialization overhead)

---

## Dependency Choices

### Messaging SDKs
| SDK | Platform | Rationale |
|-----|----------|-----------|
| `discord.js` | Discord | De facto standard, full API coverage |
| `@slack/bolt` | Slack | Official Slack SDK |
| `grammY` | Telegram | Modern, TypeScript-first Telegram framework |
| `@whiskeysockets/baileys` | WhatsApp | Community reverse-engineer (no official API) |
| `signal-cli` (subprocess) | Signal | Only option for Signal without rewriting protocol |

### Build & Dev Tools
| Tool | Purpose | Rationale |
|------|---------|-----------|
| `pnpm` | Package manager | Fast, disk-efficient, native workspace support |
| `esbuild` | Bundling | 10-100x faster than webpack/rollup |
| `tsx` | TS execution | Fast TypeScript runner for dev |
| `vitest` | Testing | Vite-native, fast, compatible with Jest API |
| `oxlint` / `oxfmt` | Linting/formatting | Rust-based, much faster than ESLint/Prettier |

### AI/ML
| Library | Purpose | Rationale |
|---------|---------|-----------|
| Anthropic SDK | Claude API | Official SDK, streaming support |
| OpenAI SDK | ChatGPT API | Official SDK, function calling |
| `node-llama-cpp` | Local LLM | Run models locally via llama.cpp |

### Media Processing
| Library | Purpose | Rationale |
|---------|---------|-----------|
| `sharp` | Image processing | Fast native image manipulation |
| `ffmpeg` (subprocess) | Audio/video | Industry standard media processing |
| `@napi-rs/canvas` | Canvas rendering | Native canvas API in Node.js |

### Native/Binary
| Library | Purpose | Rationale |
|---------|---------|-----------|
| `@lydell/node-pty` | Pseudoterminal | Required for interactive shell in system.run |
| `node-edge-tts` | Text-to-speech | Microsoft Edge TTS (free, high quality) |

---

## Security Design Decisions

### DM Pairing Policy (vs. Open Access)
**Decision:** Default to "pairing" for DMs — unknown senders must be approved.

**Reasoning:**
- Prevents unauthorized access to the AI agent
- First message from unknown user generates a pairing code
- User must confirm via another channel or the CLI
- Can be overridden to "open" for public-facing bots

### system.run Approval (vs. Auto-execute)
**Decision:** Shell command execution requires explicit user approval.

**Reasoning:**
- AI-generated commands could be destructive
- Approval flow shows the exact command before execution
- Optional Docker sandbox provides additional isolation
- Configurable allowlists restrict accessible paths

### Loopback-only Default (vs. Network-facing)
**Decision:** Gateway binds to loopback (127.0.0.1) by default.

**Reasoning:**
- Personal AI assistant — designed for single-user local use
- Network exposure requires explicit opt-in (token auth or Tailscale)
- Reduces attack surface for default installations

---

## Testing & Quality Decisions

### Vitest (vs. Jest)
**Decision:** Use Vitest for all testing.

**Reasoning:**
- Native ESM support (Jest requires transformers for ESM)
- Vite-compatible hot module replacement during test development
- Jest-compatible API for easy migration
- V8 coverage built-in

### Colocated Tests (vs. Separate Test Directory)
**Decision:** Unit tests live alongside source files (`*.test.ts`).

**Reasoning:**
- Easier to find and maintain tests
- Encourages testing during development
- Integration and E2E tests in separate directories (`test/`)
- Live tests gated by environment variables

### oxlint + oxfmt (vs. ESLint + Prettier)
**Decision:** Rust-based linting and formatting tools.

**Reasoning:**
- 10-50x faster execution on large codebase
- Less configuration overhead
- Pre-commit hooks run quickly

---

## Deployment Decisions

### Docker + fly.io (vs. Kubernetes/Cloud Functions)
**Decision:** Docker containers deployed to fly.io.

**Reasoning:**
- Single-process architecture doesn't need orchestration
- fly.io provides simple, affordable hosting with edge locations
- Docker ensures consistent environments
- Volume mounts for persistent config/session state

### Daemon Mode (vs. Always-On Server)
**Decision:** Support systemd/launchd daemon installation.

**Reasoning:**
- Personal AI assistant should auto-start with the OS
- `openclaw onboard --install-daemon` handles setup
- Background process with health monitoring
- Graceful restart on failure
