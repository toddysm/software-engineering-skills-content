# Security Overview — OpenClaw

**Date:** 2026-03-18

---

## Security Model Summary

OpenClaw implements a **local-first security model** with defense-in-depth for a personal AI assistant:

### Trust Boundaries

```
┌─────────────────────────────────────────────────────┐
│  TRUSTED ZONE (Local Device)                         │
│  ┌─────────────────────────────────────────────┐    │
│  │  Gateway (ws://127.0.0.1:18789)             │    │
│  │  ├─ CLI (same process)                      │    │
│  │  ├─ Config files (~/.openclaw/)             │    │
│  │  └─ Session store (local filesystem)        │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  SEMI-TRUSTED (Authenticated Channels)               │
│  ├─ Mobile apps (iOS/Android via WebSocket + token)  │
│  ├─ Web UI (auth token required)                     │
│  └─ Tailscale remote access                          │
│                                                      │
│  UNTRUSTED (External Input)                          │
│  ├─ DM messages from messaging platforms             │
│  ├─ Group messages mentioning the bot                │
│  ├─ Webhook payloads                                 │
│  └─ LLM-generated tool calls                         │
└─────────────────────────────────────────────────────┘
```

---

## Security Controls

### 1. Authentication & Access Control
- **Gateway auth modes:** none (loopback-only), token (defaultToken), OAuth (Tailscale)
- **DM pairing policy:** Unknown senders get a pairing code that must be approved
- **Allowlists:** Per-channel user whitelists in config
- **Rate limiting:** Built-in to prevent brute-force on token auth

### 2. Tool Execution Safety
- **system.run approval:** Shell commands require explicit user confirmation
- **Docker sandbox:** Optional isolation for untrusted code execution
- **Tool allowlists/denylists:** Per-agent path restrictions
- **Approval timeouts:** Pending tool approvals expire

### 3. Credential Management
- **Environment variables only:** API keys use `$VAR` interpolation in config
- **No plaintext secrets in config files:** Zod validation warns on plaintext
- **Secrets management:** Dedicated `src/secrets/` module
- **Session encryption:** Optional at-rest encryption for session data

### 4. Network Security
- **Loopback-only default:** Gateway binds to 127.0.0.1
- **Explicit opt-in for remote access:** Tailscale Funnel or SSH tunneling required
- **HTTPS enforcement:** Remote connections require TLS
- **WebSocket origin validation:** Prevents cross-origin attacks

---

## Areas of Concern

### High Priority
1. **WhatsApp integration (Baileys):** Uses community reverse-engineered protocol — not officially supported by Meta. Potential for account bans or protocol changes.
2. **system.run command scope:** Even with approval flow, the shell has full user permissions. Sandbox mode should be the default, not opt-in.
3. **Extension supply chain:** 76 extensions loaded at boot — compromised extension could affect all channels.

### Medium Priority
4. **Session data at rest:** Session history contains full conversation text. If not encrypted, readable by anyone with filesystem access.
5. **Config file permissions:** `~/.openclaw/config.yaml` may contain API key references. File permissions should be 600.
6. **Logging scope:** Log files may contain message content or credentials if verbose logging is enabled.

### Low Priority
7. **One circular dependency** in UI layer — low security impact but indicates coupling.
8. **Low documentation coverage** (7%) makes security auditing harder.

---

## Security Architecture Strengths

1. **Local-first design:** Minimizes network attack surface
2. **Explicit pairing for DMs:** Prevents unauthorized access to the AI agent
3. **Tool approval flow:** Human-in-the-loop for dangerous operations
4. **Zod validation:** Runtime config validation catches malformed input
5. **CODEOWNERS:** Critical paths require review approval
6. **Pre-commit hooks:** detect-secrets baseline prevents credential commits
7. **SECURITY.md:** Documented security policy and vulnerability disclosure process

---

*For the full security vulnerability analysis, see `security/detailed-security-analysis.md`.*
