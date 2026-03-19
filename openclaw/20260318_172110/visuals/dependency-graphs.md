# Dependency Graphs — OpenClaw

**Date:** 2026-03-18

---

## 1. Extension → Core Dependency Map

```mermaid
graph TD
    subgraph "Channel Extensions"
        E_Discord["extensions/discord"]
        E_Slack["extensions/slack"]
        E_Telegram["extensions/telegram"]
        E_WA["extensions/whatsapp"]
        E_Signal["extensions/signal"]
    end

    subgraph "Provider Extensions"
        E_OpenAI["extensions/openai"]
        E_Anthropic["extensions/anthropic"]
        E_Google["extensions/google"]
        E_Ollama["extensions/ollama"]
    end

    subgraph "Core Interfaces"
        I_Channel["ChannelPlugin<br/>(src/channels/plugins/types.plugin.ts)"]
        I_Provider["ProviderPlugin<br/>(src/plugins/types.ts)"]
        I_Shared["extensions/shared"]
    end

    subgraph "Core Engine"
        Loader["src/plugins/loader.ts"]
        Registry["src/plugins/registry.ts"]
        GW["src/gateway/"]
    end

    E_Discord --> I_Channel
    E_Slack --> I_Channel
    E_Telegram --> I_Channel
    E_WA --> I_Channel
    E_Signal --> I_Channel

    E_OpenAI --> I_Provider
    E_Anthropic --> I_Provider
    E_Google --> I_Provider
    E_Ollama --> I_Provider

    E_Discord --> I_Shared
    E_Slack --> I_Shared
    E_Telegram --> I_Shared
    E_OpenAI --> I_Shared
    E_Anthropic --> I_Shared

    I_Channel --> Registry
    I_Provider --> Registry
    Loader --> Registry
    Registry --> GW
```

---

## 2. Agent Execution Dependency Chain

```mermaid
graph LR
    Runner["pi-embedded-runner.ts"]
    Subscribe["pi-embedded-subscribe.ts"]
    Tools["pi-tools.ts"]
    Bash["bash-tools.ts"]
    Skills["agents/skills/"]
    Models["model-*.ts"]
    SubAgent["subagent-*.ts"]

    Runner --> Subscribe
    Runner --> Tools
    Runner --> Models
    Runner --> SubAgent
    Tools --> Bash
    Tools --> Skills
    Subscribe --> Tools

    style Runner fill:#E74C3C,color:#fff
```

---

## 3. Configuration Dependency Chain

```mermaid
graph TD
    YAML["config.yaml<br/>(user file)"]
    Loader["config.ts<br/>(loader)"]
    ZodSchema["zod-schema.*.ts<br/>(validation)"]
    Types["types.ts<br/>(definitions)"]
    Legacy["legacy.ts<br/>(migrations)"]
    Sessions["sessions.ts<br/>(store)"]
    Hints["schema.hints.ts<br/>(help text)"]

    YAML --> Loader
    Loader --> ZodSchema
    ZodSchema --> Types
    Loader --> Legacy
    Loader --> Sessions
    ZodSchema --> Hints

    style Loader fill:#2ECC71,color:#fff
```

---

## 4. Circular Dependencies

Only **1 circular dependency** was detected in the entire codebase:

```mermaid
graph LR
    A["ui/src/ui/app-settings.ts"] --> B["ui/src/ui/app-chat.ts"]
    B --> A

    style A fill:#F39C12,color:#fff
    style B fill:#F39C12,color:#fff
```

**Impact:** Low — limited to the web UI layer. The settings and chat views reference each other, likely through shared state or navigation.

---

## 5. Dependency Statistics

| Metric | Value |
|--------|-------|
| Total files analyzed | 12,136 |
| Total dependency edges | 20,370 |
| Circular dependencies | 1 |
| Average deps per file | 1.7 |
| Max dependents (most-imported file) | See impact analysis |

---

## 6. Skill → Tool Dependency Map

```mermaid
graph TD
    subgraph "Skill Categories"
        S_Prod["Productivity Skills"]
        S_Dev["Development Skills"]
        S_Comm["Communication Skills"]
        S_Media["Media Skills"]
        S_Voice["Voice Skills"]
        S_Home["Smart Home Skills"]
    end

    subgraph "Core Tools"
        T_Browser["Browser Tool"]
        T_Shell["system.run"]
        T_Canvas["Canvas"]
        T_ImgGen["Image Generation"]
        T_Cron["Cron"]
        T_Memory["Memory"]
    end

    subgraph "Agent"
        Agent["Pi Agent Runtime"]
    end

    S_Prod --> Agent
    S_Dev --> Agent
    S_Comm --> Agent
    S_Media --> Agent
    S_Voice --> Agent
    S_Home --> Agent

    Agent --> T_Browser
    Agent --> T_Shell
    Agent --> T_Canvas
    Agent --> T_ImgGen
    Agent --> T_Cron
    Agent --> T_Memory
```
