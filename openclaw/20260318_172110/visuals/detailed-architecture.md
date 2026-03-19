# Detailed Architecture Diagrams — OpenClaw

**Date:** 2026-03-18

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "User Interfaces"
        CLI["CLI<br/>(openclaw.mjs)"]
        WebUI["Web Dashboard<br/>(ui/)"]
        iOS["iOS App<br/>(apps/ios/)"]
        macOS["macOS App<br/>(apps/macos/)"]
        Android["Android App<br/>(apps/android/)"]
    end

    subgraph "Messaging Channels"
        WA["WhatsApp"]
        TG["Telegram"]
        SL["Slack"]
        DC["Discord"]
        SIG["Signal"]
        iMsg["iMessage"]
        MTX["Matrix"]
        Teams["MS Teams"]
        IRC2["IRC"]
        MORE["... 16 more"]
    end

    subgraph "Gateway Control Plane"
        GW["WebSocket Server<br/>ws://127.0.0.1:18789"]
        Auth["Auth Module"]
        SM["Session Manager"]
        Router["Routing Engine"]
        ChanMgr["Channel Manager"]
        PlugMgr["Plugin Manager"]
        HookSys["Hook System"]
    end

    subgraph "Agent Runtime"
        Pi["Pi Agent Runner"]
        Tools["Tool Executor"]
        Skills["Skill Loader"]
        SubAgent["Sub-Agent Manager"]
        Stream["Stream Handler"]
    end

    subgraph "LLM Providers"
        Anthropic["Anthropic<br/>(Claude)"]
        OpenAI["OpenAI<br/>(GPT-4)"]
        Google["Google<br/>(Gemini)"]
        Ollama["Ollama<br/>(Local)"]
        Bedrock["AWS Bedrock"]
        MoreProv["... 15 more"]
    end

    subgraph "Storage"
        Config["Config<br/>(~/.openclaw/config.yaml)"]
        Sessions["Session Store<br/>(filesystem)"]
        Memory["Memory<br/>(LanceDB)"]
    end

    CLI --> GW
    WebUI --> GW
    iOS --> GW
    macOS --> GW
    Android --> GW

    WA --> ChanMgr
    TG --> ChanMgr
    SL --> ChanMgr
    DC --> ChanMgr
    SIG --> ChanMgr
    iMsg --> ChanMgr
    MTX --> ChanMgr
    Teams --> ChanMgr
    IRC2 --> ChanMgr
    MORE --> ChanMgr

    GW --> Auth
    GW --> SM
    GW --> Router
    GW --> ChanMgr
    GW --> PlugMgr
    GW --> HookSys

    Router --> Pi
    Pi --> Tools
    Pi --> Skills
    Pi --> SubAgent
    Pi --> Stream

    Pi --> Anthropic
    Pi --> OpenAI
    Pi --> Google
    Pi --> Ollama
    Pi --> Bedrock
    Pi --> MoreProv

    SM --> Sessions
    GW --> Config
    Pi --> Memory

    style GW fill:#4A90D9,color:#fff
    style Pi fill:#E74C3C,color:#fff
    style ChanMgr fill:#27AE60,color:#fff
    style PlugMgr fill:#F39C12,color:#fff
```

---

## 2. Message Flow Sequence

```mermaid
sequenceDiagram
    participant User
    participant Channel as Channel Plugin<br/>(e.g., Slack)
    participant Gateway as Gateway<br/>Control Plane
    participant Session as Session<br/>Manager
    participant Router as Routing<br/>Engine
    participant Agent as Pi Agent<br/>Runtime
    participant LLM as LLM Provider<br/>(e.g., Claude)
    participant Tool as Tool<br/>Executor

    User->>Channel: Send message
    Channel->>Channel: Normalize to ChannelMessage
    Channel->>Gateway: Emit inbound event
    Gateway->>Session: Resolve session key
    Session-->>Gateway: Session context + history
    Gateway->>Gateway: Validate allowlist
    Gateway->>Router: Select agent for route
    Router-->>Gateway: Agent binding
    Gateway->>Agent: Dispatch to Pi agent
    Agent->>Agent: Build system prompt + tools
    Agent->>LLM: Send messages (streaming)
    
    loop Streaming Response
        LLM-->>Agent: Token stream
        Agent->>Agent: Buffer text blocks
        
        opt Tool Call
            LLM-->>Agent: ToolUseBlock
            Agent->>Tool: Execute tool
            Tool-->>Agent: ToolResultBlock
            Agent->>LLM: Feed result back
        end
    end
    
    Agent->>Session: Save final history
    Agent-->>Gateway: Complete response
    Gateway->>Channel: Route reply
    Channel->>User: Send formatted response
```

---

## 3. Plugin System Architecture

```mermaid
graph LR
    subgraph "Core Plugin Framework (src/plugins/)"
        Loader["Plugin Loader"]
        Registry["Plugin Registry"]
        Runtime["Plugin Runtime"]
        Hooks["Hook Dispatcher"]
        Manifest["Manifest Parser"]
    end

    subgraph "Channel Plugins (extensions/)"
        CP_Discord["discord/"]
        CP_Slack["slack/"]
        CP_Telegram["telegram/"]
        CP_WA["whatsapp/"]
        CP_Signal["signal/"]
        CP_More["... 20+ more"]
    end

    subgraph "Provider Plugins (extensions/)"
        PP_OpenAI["openai/"]
        PP_Anthropic["anthropic/"]
        PP_Google["google/"]
        PP_Ollama["ollama/"]
        PP_More["... 15+ more"]
    end

    subgraph "Feature Plugins (extensions/)"
        FP_Memory["memory-lancedb/"]
        FP_Voice["voice-call/"]
        FP_Diffs["diffs/"]
        FP_Diag["diagnostics-otel/"]
    end

    Loader --> Manifest
    Manifest --> Registry
    Registry --> Runtime
    Runtime --> Hooks

    CP_Discord --> Registry
    CP_Slack --> Registry
    CP_Telegram --> Registry
    CP_WA --> Registry
    CP_Signal --> Registry
    CP_More --> Registry

    PP_OpenAI --> Registry
    PP_Anthropic --> Registry
    PP_Google --> Registry
    PP_Ollama --> Registry
    PP_More --> Registry

    FP_Memory --> Registry
    FP_Voice --> Registry
    FP_Diffs --> Registry
    FP_Diag --> Registry

    style Loader fill:#4A90D9,color:#fff
    style Registry fill:#4A90D9,color:#fff
    style Runtime fill:#4A90D9,color:#fff
```

---

## 4. Core Module Dependencies

```mermaid
graph TD
    CLI["src/cli/"]
    GW["src/gateway/"]
    Agents["src/agents/"]
    Channels["src/channels/"]
    Config["src/config/"]
    Plugins["src/plugins/"]
    Providers["src/providers/"]
    Sessions["src/sessions/"]
    Routing["src/routing/"]
    Types["src/types/"]
    Shared["src/shared/"]
    Hooks["src/hooks/"]
    Memory["src/memory/"]
    Media["src/media/"]
    Browser["src/browser/"]
    Cron["src/cron/"]
    Terminal["src/terminal/"]
    TTS["src/tts/"]
    Security["src/security/"]

    CLI --> GW
    CLI --> Config
    CLI --> Agents

    GW --> Agents
    GW --> Channels
    GW --> Config
    GW --> Plugins
    GW --> Sessions
    GW --> Routing
    GW --> Hooks

    Agents --> Providers
    Agents --> Config
    Agents --> Sessions
    Agents --> Plugins
    Agents --> Memory
    Agents --> Browser
    Agents --> Terminal

    Channels --> Config
    Channels --> Sessions
    Channels --> Plugins

    Plugins --> Config
    Plugins --> Types
    Plugins --> Hooks

    Providers --> Plugins
    Providers --> Config

    Routing --> Config
    Routing --> Sessions

    Sessions --> Config
    Sessions --> Shared

    Config --> Types

    Media --> Shared
    Browser --> Shared
    Cron --> Config
    TTS --> Config
    Security --> Config

    style GW fill:#4A90D9,color:#fff
    style Agents fill:#E74C3C,color:#fff
    style Config fill:#2ECC71,color:#fff
    style Plugins fill:#F39C12,color:#fff
```

---

## 5. Deployment Architecture

```mermaid
graph TB
    subgraph "Local Installation"
        NPM["npm install -g openclaw"]
        Daemon["systemd/launchd daemon"]
        LocalGW["Gateway<br/>ws://127.0.0.1:18789"]
    end

    subgraph "Docker Deployment"
        DC_GW["openclaw-gateway<br/>(Port 18789)"]
        DC_CLI["openclaw-cli<br/>(network_mode: service)"]
        DC_Vol["Config Volume<br/>~/.openclaw/"]
    end

    subgraph "Cloud (fly.io)"
        Fly["fly.io Instance"]
        TS["Tailscale Serve"]
        FlyVol["Persistent Volume"]
    end

    subgraph "Clients"
        C_CLI["CLI"]
        C_iOS["iOS App"]
        C_Android["Android App"]
        C_macOS["macOS App"]
        C_Web["Web UI"]
    end

    NPM --> Daemon
    Daemon --> LocalGW

    DC_GW --- DC_CLI
    DC_Vol --> DC_GW

    Fly --> TS
    FlyVol --> Fly

    C_CLI --> LocalGW
    C_iOS --> LocalGW
    C_Android --> LocalGW
    C_macOS --> LocalGW
    C_Web --> LocalGW

    C_CLI -.-> DC_GW
    C_iOS -.-> TS
    C_Web -.-> TS

    style LocalGW fill:#4A90D9,color:#fff
    style DC_GW fill:#4A90D9,color:#fff
    style Fly fill:#9B59B6,color:#fff
```

---

## 6. Security Architecture

```mermaid
graph TB
    subgraph "Public Zone (Internet)"
        ExtMsg["External Messages<br/>(Slack, Telegram, etc.)"]
        Webhooks["Webhooks"]
    end

    subgraph "DMZ (Authenticated Access)"
        TailscaleF["Tailscale Funnel"]
        TokenAuth["Token Auth"]
    end

    subgraph "Trusted Zone (Loopback)"
        GW["Gateway<br/>127.0.0.1:18789"]
        
        subgraph "Security Controls"
            Allowlist["User Allowlists"]
            Pairing["DM Pairing Policy"]
            ToolApproval["Tool Approval Flow"]
            Sandbox["Docker Sandbox"]
            RateLimit["Rate Limiting"]
        end
        
        subgraph "Protected Resources"
            Config2["Config + Secrets"]
            SessionData["Session History"]
            FileSystem["Local Filesystem"]
            Shell["Shell Access"]
        end
    end

    ExtMsg --> Allowlist
    Webhooks --> TokenAuth
    TailscaleF --> GW
    TokenAuth --> GW

    Allowlist --> GW
    Pairing --> GW
    GW --> ToolApproval
    ToolApproval --> Sandbox
    Sandbox --> Shell
    GW --> SessionData
    GW --> Config2
    ToolApproval --> FileSystem
    RateLimit --> GW

    style GW fill:#4A90D9,color:#fff
    style Allowlist fill:#E74C3C,color:#fff
    style Pairing fill:#E74C3C,color:#fff
    style ToolApproval fill:#E74C3C,color:#fff
    style Sandbox fill:#E74C3C,color:#fff
    style RateLimit fill:#E74C3C,color:#fff
```
