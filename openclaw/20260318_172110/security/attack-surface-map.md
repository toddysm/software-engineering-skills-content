# Attack Surface Map — OpenClaw

## Overview

OpenClaw's attack surface spans multiple trust boundaries: external messaging platforms, LLM providers, local network interfaces, the plugin system, and LLM-generated tool invocations.

---

## External Input Points

### 1. WebSocket Gateway (Primary Control Plane)
- **Endpoint:** `ws://127.0.0.1:18789`
- **Protocol:** WebSocket
- **Authentication:** Token-based (constant-time comparison via `timingSafeEqual`)
- **Authorization:** Role-based method-level RBAC
- **Rate limiting:** Yes, with loopback exemption
- **Input validation:** Zod schema validation on messages
- **Exposed to:** Local network; can be exposed via SSH tunnels, reverse proxies, or Tailscale
- **Risk:** HIGH — primary entry point for all control operations

### 2. Channel Plugin Ingress (25+ platforms)
- **Platforms:** Discord, Slack, Telegram, WhatsApp, Signal, iMessage, Matrix, SMS, Email, Web Chat, etc.
- **Protocol:** Platform-specific (HTTP webhooks, WebSocket, XMPP, etc.)
- **Authentication:** Platform-provided tokens/signatures
- **Input validation:** External content wrapping (prompt injection mitigation)
- **Risk:** HIGH — each channel is an untrusted input source carrying user messages

### 3. LLM Provider APIs (20+ providers)
- **Providers:** OpenAI, Anthropic, Google, xAI, Azure, AWS, Ollama, etc.
- **Protocol:** HTTPS REST APIs
- **Direction:** Outbound (but responses are processed as input)
- **Risk:** MEDIUM — LLM responses influence tool execution decisions

### 4. Node Host Communication
- **Protocol:** WebSocket (node.invoke)
- **Direction:** Bidirectional
- **Authentication:** Token-based
- **Risk:** HIGH — remote code execution capability via system.run

### 5. HTTP API Endpoints
- **Endpoint:** Express-based HTTP server
- **Exposed routes:** Health checks, webhook receivers, static assets
- **Authentication:** Varies by route
- **Risk:** MEDIUM — depends on exposed surface

---

## Internal Execution Boundaries

### 6. Bash Tool Execution
- **Trigger:** LLM agent requests shell command execution
- **Validation:** `validateScriptFileForShellBleed()` preflight, human approval system
- **Isolation:** Docker sandbox containers (optional)
- **Risk:** HIGH — direct OS command execution

### 7. Plugin Code Execution
- **Trigger:** Gateway startup, dynamic plugin loading
- **Loader:** `jiti` (TypeScript/ESM loader)
- **Isolation:** None — runs in gateway process
- **Risk:** HIGH — full process access

### 8. Agent/Skill Execution
- **Trigger:** Multi-step LLM task orchestration
- **52 skills:** File operations, web browsing, screen capture, code execution, etc.
- **Risk:** MEDIUM — controlled via tool policy system

### 9. Docker Sandbox
- **Trigger:** Tool execution requiring isolation
- **Image:** Custom `Dockerfile.sandbox*`
- **Bind mounts:** Validated via `validate-sandbox-security.ts`
- **Risk:** MEDIUM — container escape is low probability but high impact

---

## Data Flow Trust Boundaries

```
┌─────────────────────────────────────────────────────────┐
│ EXTERNAL (Untrusted)                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Discord  │  │ Slack    │  │ Telegram │  ... 22 more   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │                     │
│  ═════╪══════════════╪══════════════╪═══ TRUST BOUNDARY 1 │
│       │              │              │                     │
│  ┌────▼──────────────▼──────────────▼─────┐              │
│  │   Channel Plugins (message normalization)│             │
│  │   + External Content Wrapping            │             │
│  └────────────────┬───────────────────────┘              │
│                   │                                       │
│  ═════════════════╪═════════════════ TRUST BOUNDARY 2     │
│                   │                                       │
│  ┌────────────────▼───────────────────────┐              │
│  │        Gateway Core                     │              │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ │              │
│  │  │  Auth   │ │ Sessions │ │ Router  │ │              │
│  │  └─────────┘ └──────────┘ └────┬────┘ │              │
│  │                                │       │              │
│  │  ══════════════════════════════╪═ TB 3 │              │
│  │                                │       │              │
│  │  ┌────────────────────────────▼────┐  │              │
│  │  │      Pi Agent Runtime            │  │              │
│  │  │  ┌─────────┐  ┌──────────────┐  │  │              │
│  │  │  │ Tool    │  │  Sandbox     │  │  │              │
│  │  │  │ Policy  │  │  Validator   │  │  │              │
│  │  │  └────┬────┘  └──────┬───────┘  │  │              │
│  │  │       │               │          │  │              │
│  │  │  ═════╪═══════════════╪═══ TB 4  │  │              │
│  │  │       │               │          │  │              │
│  │  │  ┌────▼───┐    ┌─────▼──────┐   │  │              │
│  │  │  │ Bash   │    │  Docker    │   │  │              │
│  │  │  │ Tools  │    │  Sandbox   │   │  │              │
│  │  │  └────────┘    └────────────┘   │  │              │
│  │  └─────────────────────────────────┘  │              │
│  └────────────────────────────────────────┘              │
│                                                          │
│  ═══════════════════════════════════ TRUST BOUNDARY 5     │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ OpenAI   │  │Anthropic │  │ Google   │  ... 17 more   │
│  └──────────┘  └──────────┘  └──────────┘               │
│ EXTERNAL (Semi-trusted)                                  │
└─────────────────────────────────────────────────────────┘
```

---

## Trust Boundaries Summary

| # | Boundary | From | To | Controls |
|---|----------|------|----|----------|
| TB1 | Platform → Channel Plugin | Untrusted user messages | Plugin ingress | Platform auth, content wrapping |
| TB2 | Channel Plugin → Gateway | Normalized messages | Core routing | Session auth, role checks |
| TB3 | Gateway → Agent Runtime | Routing decisions | LLM orchestration | Tool policies, approval system |
| TB4 | Agent → Execution | Tool invocations | OS/Docker | Sandbox validation, path restriction, approval |
| TB5 | Gateway → LLM Providers | Prompts (contain user data) | External API | TLS, API key auth, SSRF protection |

---

## Sensitive Data Assets

| Asset | Location | Protection |
|-------|----------|------------|
| API keys (20+ providers) | Environment variables, config YAML | Zod-validated config, `.env` file |
| User conversation history | In-memory sessions, optional persistence | Session isolation |
| Authentication tokens | Gateway runtime | `timingSafeEqual` comparison |
| Plugin source code | `extensions/` directory | File-system permissions |
| Sandbox bind mounts | Docker runtime | Path validation, dangerous-path blocking |
| WebSocket control messages | In-transit | Local-only binding (127.0.0.1) |

---

## Network Exposure

| Interface | Default Binding | Protocol | Authentication |
|-----------|----------------|----------|---------------|
| WebSocket Gateway | 127.0.0.1:18789 | WS | Token |
| HTTP Server | Configurable | HTTP/HTTPS | Route-specific |
| Webhook receivers | Public (when configured) | HTTPS | Platform signatures |
| Docker socket | /var/run/docker.sock | Unix | File permissions |
| Node host connections | Configurable | WS | Token |

---

## Attack Vectors

### V1: Prompt Injection via Channel Message
**Path:** User message → Channel plugin → Agent → Tool execution  
**Mitigations:** External content wrapping, tool approval system  
**Residual risk:** LLM may still be manipulated

### V2: Malicious Plugin Installation
**Path:** Plugin directory → jiti loader → Gateway process  
**Mitigations:** File-system access control only  
**Residual risk:** No code signing or sandboxing

### V3: Dependency Supply Chain
**Path:** npm package → pnpm install → Runtime  
**Mitigations:** Lock file, pnpm strict mode  
**Residual risk:** No integrity verification beyond lock file

### V4: Network-Adjacent Gateway Access
**Path:** SSH tunnel/reverse proxy → WebSocket → Gateway commands  
**Mitigations:** Token auth, rate limiting  
**Residual risk:** Loopback exemption bypass

### V5: Sandbox Escape
**Path:** Docker container → Host filesystem  
**Mitigations:** Bind mount validation, dangerous path blocking  
**Residual risk:** Symlink/case-sensitivity bypasses
