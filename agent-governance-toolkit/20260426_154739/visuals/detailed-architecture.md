# Detailed Architecture Diagrams — Agent Governance Toolkit

These diagrams complement [../documentation.md](../documentation.md) §3 with progressively more detailed views of the system.

---

## 1. High-level subsystem map

```mermaid
graph TB
    subgraph Consumers["Agent runtime (host application)"]
        APP[Agent code<br/>Python · TS · .NET · Rust · Go]
    end

    subgraph SDKs["Language SDKs (canonical homes)"]
        PYSDK[agent-governance-python]
        DOTSDK[agent-governance-dotnet]
        TSSDK[agent-governance-typescript]
        RSSDK[agent-governance-rust]
        GOSDK[agent-governance-golang]
    end

    subgraph Runtime["Python runtime / packages/"]
        AOS[agent-os<br/>kernel · modules · charts]
        AMESH[agent-mesh<br/>identity · governance]
        ARUN[agent-runtime]
        AHYP[agent-hypervisor]
        ASRE[agent-sre]
        ACOMP[agent-compliance]
        ADISC[agent-discovery]
    end

    subgraph Plane["Governance plane (logical)"]
        POL[Policy Evaluator]
        TRUST[Trust / Identity]
        HYP[Hypervisor / KillSwitch / Rings]
        AUD[Audit / Telemetry / SLO]
        MCPGW[MCP Gateway / Sanitizer / Redactor]
    end

    subgraph Integrations["packages/agentmesh-integrations/"]
        LC[langchain]
        LG[langgraph-trust]
        LI[llamaindex]
        CR[crewai]
        OAI[openai-agents]
        MAF[Microsoft Agent Framework]
        OTHER[20+ adapters]
    end

    APP --> PYSDK & DOTSDK & TSSDK & RSSDK & GOSDK
    PYSDK --> AOS & AMESH
    DOTSDK --> POL & TRUST & HYP & AUD & MCPGW
    TSSDK --> POL & MCPGW
    RSSDK --> MCPGW & AUD
    GOSDK --> TRUST & MCPGW

    AOS --> POL & AUD
    AMESH --> TRUST & POL
    AHYP --> HYP
    ASRE --> AUD
    ACOMP --> AUD
    ADISC --> TRUST

    Integrations --> POL
    APP -.observed-by.-> Integrations

    classDef plane fill:#fef3c7,stroke:#d97706
    classDef sdk fill:#dbeafe,stroke:#2563eb
    classDef runtime fill:#ecfccb,stroke:#65a30d
    classDef integration fill:#fce7f3,stroke:#db2777

    class POL,TRUST,HYP,AUD,MCPGW plane
    class PYSDK,DOTSDK,TSSDK,RSSDK,GOSDK sdk
    class AOS,AMESH,ARUN,AHYP,ASRE,ACOMP,ADISC runtime
    class LC,LG,LI,CR,OAI,MAF,OTHER integration
```

---

## 2. Policy decision flow

```mermaid
sequenceDiagram
    autonumber
    participant Agent
    participant SDK as SDK Hook
    participant TV as TrustVerifier
    participant PE as PolicyEvaluator
    participant EP as ExternalPolicyBackend (optional)
    participant H as Hypervisor
    participant A as AuditLogger
    participant T as Tool / MCP Server

    Agent->>SDK: invoke(action, args, identity)
    SDK->>TV: verify(identity)
    TV-->>SDK: Verified Principal
    SDK->>PE: evaluate(action, args, principal)
    PE->>EP: optional external rules
    EP-->>PE: decision contribution
    PE->>PE: ConflictResolution
    PE-->>SDK: ALLOW | DENY | REDACT

    alt DENY
        SDK->>A: append(GovernanceEvent: denied)
        SDK-->>Agent: DenyError
    else ALLOW
        SDK->>H: enter ExecutionRing(args)
        H->>T: invoke
        T-->>H: response
        H-->>SDK: response
        SDK->>A: append(GovernanceEvent: allowed)
        SDK-->>Agent: response
    else REDACT
        SDK->>H: enter ExecutionRing(args)
        H->>T: invoke
        T-->>H: response
        H->>SDK: McpResponseSanitizer + McpCredentialRedactor
        SDK->>A: append(GovernanceEvent: redacted)
        SDK-->>Agent: redacted response
    end
```

---

## 3. .NET subsystem detail (canonical reference for cross-language SDKs)

```mermaid
graph LR
    subgraph dotnet["agent-governance-dotnet/src/AgentGovernance"]
        GK[GovernanceKernel.cs]
        subgraph PolicyNS["Policy/"]
            P1[Policy.cs]
            P2[PolicyDecision.cs]
            P3[ConflictResolution.cs]
            P4[ExternalPolicyBackend.cs]
        end
        subgraph TrustNS["Trust/"]
            T1[TrustVerifier.cs]
            T2[IdentityRegistry.cs]
            T3[FileTrustStore.cs]
            T4[Jwk.cs]
        end
        subgraph DiscoveryNS["Discovery/"]
            D1[ConfigScanner.cs]
            D2[ProcessScanner.cs]
            D3[RiskScorer.cs]
            D4[Reconciler.cs]
            D5[AgentInventory.cs]
            D6[DiscoveryModels.cs]
        end
        subgraph McpNS["Mcp/"]
            M1[McpGateway.cs]
            M2[McpSecurityScanner.cs]
            M3[McpCredentialRedactor.cs]
            M4[McpResponseSanitizer.cs]
        end
        subgraph HypNS["Hypervisor/"]
            H1[KillSwitch.cs]
            H2[ExecutionRings.cs]
        end
        subgraph SreNS["Sre/"]
            S1[SloEngine.cs]
        end
        subgraph AuditNS["Audit/"]
            A1[AuditLogger.cs]
            A2[GovernanceEvent.cs]
        end
        subgraph SecNS["Security/"]
            X1[PromptInjectionDetector.cs]
            X2[PromptDefenseEvaluator.cs]
        end
        subgraph LifecycleNS["Lifecycle/"]
            L1[LifecycleManager.cs]
        end
        subgraph TelemetryNS["Telemetry/"]
            TE1[GovernanceMetrics.cs]
        end
    end

    subgraph Extensions["Extensions"]
        E1[Extensions.ModelContextProtocol]
        E2[Extensions.Microsoft.Agents]
    end

    GK --> P1
    GK --> T1
    GK --> M1
    GK --> H1
    GK --> A1
    GK --> X1
    GK --> L1
    GK --> TE1

    P1 --> P3
    P3 --> P2
    P1 --> P4

    T1 --> T2
    T1 --> T4
    T2 --> T3

    M1 --> M2
    M1 --> M3
    M1 --> M4

    D1 --> D5
    D2 --> D5
    D5 --> D3
    D5 --> D4
    D5 --> D6

    H1 --> A1
    H2 --> A1

    E1 --> M1
    E2 --> GK

    classDef hot fill:#fee2e2,stroke:#dc2626
    class T3,M1 hot
```

`FileTrustStore.cs` and `McpGateway.cs` are highlighted (red) because they sit at the trust boundary and are the highest-value review targets.

---

## 4. Python runtime layer (`packages/`)

```mermaid
graph TB
    subgraph aos["packages/agent-os/"]
        AOS_SRC[src/agent_os/]
        AOS_MOD[modules/<br/>amb · atr · cmvk · scak · caas · control-plane · observability · mute-agent · emk · iatp]
        AOS_SVC[services/<br/>cloud-board]
        AOS_EXT[extensions/<br/>copilot · mcp-server · vscode]
        AOS_CHARTS[charts/agent-os/]
    end

    subgraph amesh["packages/agent-mesh/"]
        AM_ID[src/agentmesh/identity/<br/>namespace · namespace_manager]
        AM_GOV[src/agentmesh/governance/<br/>policy_evaluator]
        AM_INT[src/agentmesh/integrations/mcp/]
        AM_SDK[sdks/]
    end

    subgraph other["other packages/"]
        AHYP[agent-hypervisor/<br/>session · sandbox]
        ARUN[agent-runtime/<br/>deploy]
        ASRE[agent-sre/<br/>sbom · slos · capture]
        ACOMP[agent-compliance/<br/>security/scanner]
        ADISC[agent-discovery/<br/>scanners/process]
        AMVS[agent-os-vscode/]
    end

    subgraph integrations["packages/agentmesh-integrations/"]
        I1[langchain-agentmesh]
        I2[langgraph-trust]
        I3[llamaindex-agentmesh]
        I4[crewai-agentmesh]
        I5[openai-agents-agentmesh]
        I6[mcp-trust-proxy]
        IX[14 more...]
    end

    AOS_SRC --> AM_GOV
    AOS_MOD --> AOS_SRC
    AOS_SVC --> AOS_SRC
    AOS_EXT --> AOS_SRC
    AHYP --> AM_ID
    ARUN --> AOS_SRC
    ASRE --> AOS_SRC
    ACOMP --> AOS_SRC
    ADISC --> AM_ID

    integrations --> AM_GOV
    integrations --> AM_INT

    classDef hub fill:#fef3c7,stroke:#d97706
    class AOS_SRC,AM_GOV,AM_INT hub
```

The yellow-highlighted nodes are the runtime layer's structural hubs.

---

## 5. Repository at-a-glance (file count by language)

```mermaid
pie title Source files by language (n=2,078)
    "Python" : 1595
    "TypeScript" : 262
    "C#" : 74
    "TSX" : 49
    "Rust" : 39
    "Go" : 33
    "JavaScript" : 14
    "Kotlin" : 12
```

---

## 6. CI / release pipeline (observed)

```mermaid
graph LR
    DEV[Developer<br/>PR] --> GHA[GitHub Actions<br/>.github/workflows/ci.yml]
    GHA --> SCORE[OpenSSF Scorecard]
    GHA --> FUZZ[ClusterFuzzLite<br/>.clusterfuzzlite/]
    GHA --> TESTS[9,500+ tests across<br/>Python · TS · .NET · Rust · Go]
    DEV --> ESRP[Azure DevOps ESRP<br/>pipelines/]
    ESRP --> NUGET[NuGet]
    ESRP --> NPM[npm]
    ESRP --> PYPI[PyPI]
    ESRP --> CRATES[crates.io]

    classDef gap fill:#fee2e2,stroke:#dc2626
    GAP[Recommended additions:<br/>semgrep · gitleaks · trivy<br/>per-language dep audits]:::gap
    GHA -.proposed.-> GAP
```

---

*End of detailed architecture diagrams. The interactive force-directed graph is at [../dependencies/dependency-graph.html](../dependencies/dependency-graph.html).*
