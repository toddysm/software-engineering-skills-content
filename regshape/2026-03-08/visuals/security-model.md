# regshape — Security Model Visualization

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

---

## 1. Trust Boundaries

```mermaid
graph TB
    subgraph User["User Trust Zone"]
        CLI_USER["CLI User<br/>(full trust)"]
        FS["Local Filesystem<br/>(trusted)"]
    end

    subgraph App["Application Trust Zone"]
        APP["regshape process"]
        CREDS_MEM["Credentials in memory<br/>(runtime only)"]
    end

    subgraph System["System Trust Zone (partial trust)"]
        DOCKER_CFG["~/.docker/config.json<br/>(read-only, trusted)"]
        CRED_HELPER["docker-credential-{store}<br/>(subprocess, trusted helper)"]
        ENV_VARS["Environment Variables<br/>(DOCKER_CONFIG, etc.)"]
    end

    subgraph Registry["Remote Registry (untrusted input)"]
        REG_API["Registry HTTP API"]
        TOKEN_EP["Token Endpoint"]
    end

    CLI_USER --> |CLI args| APP
    APP --> |read| DOCKER_CFG
    APP --> |subprocess exec| CRED_HELPER
    APP --> |reads| ENV_VARS
    APP --> |stores in| CREDS_MEM
    APP --> |HTTPS| REG_API
    APP --> |HTTPS| TOKEN_EP
    CRED_HELPER --> |stored credentials| FS

    style User fill:#d5e8d4
    style App fill:#dae8fc
    style System fill:#fff2cc
    style Registry fill:#f8cecc
```

---

## 2. Credential Flow and Security Controls

```mermaid
flowchart TD
    INPUT["Input Sources"] --> E1["CLI --username/--password"]
    INPUT --> E2["DOCKER_CONFIG env var"]
    INPUT --> E3["~/.docker/config.json"]
    INPUT --> E4["docker-credential-{store}"]

    E1 --> RESOLVE["credentials.py<br/>resolve_credentials()"]
    E2 --> RESOLVE
    E3 --> RESOLVE
    E4 --> RESOLVE

    RESOLVE --> STORE["Memory: (username, password) tuple"]

    STORE --> AUTH_FLOW["registryauth.py<br/>authenticate()"]
    
    AUTH_FLOW --> |Bearer flow| TOKEN["POST token endpoint<br/>Authorization: Basic {b64(user:pass)}"]
    AUTH_FLOW --> |Basic flow| B64["Base64 encode user:pass<br/>→ Authorization: Basic header"]

    TOKEN --> |receive JWT| JWT["Short-lived access_token (JWT)"]
    JWT --> REQUEST["HTTP request<br/>Authorization: Bearer {token}"]
    B64 --> REQUEST

    REQUEST --> SANIT["sanitization.py<br/>redact_headers() for logging"]
    SANIT --> LOG["Log output<br/>Authorization: Bearer [REDACTED]"]

    style INPUT fill:#fff2cc
    style STORE fill:#ffe6cc
    style SANIT fill:#d5e8d4
    style LOG fill:#d5e8d4
```

---

## 3. Attack Surface Map

```mermaid
graph TB
    subgraph External["External Attack Surfaces"]
        S1["S1: Registry HTTP API<br/>Malformed JSON responses<br/>Response injection<br/>SSRF via redirects"]
        S2["S2: Token Endpoint<br/>Token forgery<br/>MITM for credentials"]
        S3["S3: CLI Arguments<br/>Path traversal in output paths<br/>Injection via registry URLs"]
    end

    subgraph System["System Attack Surfaces"]
        S4["S4: docker-credential-{store}<br/>subprocess PATH hijack<br/>Malicious credential helper"]
        S5["S5: ~/.docker/config.json<br/>Config file tampering<br/>Sensitive credential exposure"]
        S6["S6: --insecure flag<br/>HTTP (no TLS) attack path<br/>Credential interception"]
    end

    subgraph App["Application Weaknesses"]
        W1["W1: No request timeouts<br/>registryauth.py:116,118<br/>CWE-400 DoS vector"]
        W2["W2: Insecure temp files in tests<br/>test_auth_cli.py<br/>CWE-377 (test-only)"]
        W3["W3: assert statements in prod<br/>disabled with -O flag<br/>B101 (1232 instances)"]
        W4["W4: gitpython vulns<br/>dev environment only<br/>RCE in git operations"]
    end

    S1 --> W1
    S2 --> W1
    S6 --> S2
    S4 --> S5

    style External fill:#f8cecc
    style System fill:#ffe6cc
    style App fill:#fff2cc
```

---

## 4. Data Sensitivity Classification

```mermaid
graph LR
    subgraph Critical["Critical (never log plaintext)"]
        C1["Registry passwords"]
        C2["Bearer/Basic auth tokens"]
        C3["Private registry credentials"]
    end

    subgraph Sensitive["Sensitive (log with care)"]
        S1["Registry usernames"]
        S2["Docker config path"]
        S3["Credential helper names"]
    end

    subgraph Public["Public (safe to log)"]
        P1["Registry hostnames"]
        P2["Repository names"]
        P3["Digest values (sha256:...)"]
        P4["Tag names"]
        P5["Manifest media types"]
        P6["Blob sizes"]
    end

    subgraph Controls["Security Controls Applied"]
        SANIT["redact_headers()<br/>Authorization → Bearer [REDACTED]"]
        SCRUB["SENSITIVE_HEADERS frozenset:<br/>authorization, cookie, set-cookie,<br/>proxy-authorization"]
        BEARER_PRESERVE["Preserves auth scheme token<br/>Basic/Bearer keyword kept"]
    end

    Critical --> SANIT
    SANIT --> SCRUB
    SCRUB --> BEARER_PRESERVE

    style Critical fill:#f8cecc
    style Sensitive fill:#ffe6cc
    style Public fill:#d5e8d4
    style Controls fill:#dae8fc
```

---

## 5. TLS and Transport Security

```mermaid
flowchart LR
    DEFAULT["Default: HTTPS<br/>TLS enforced by requests library<br/>System CA bundle"] --> |--insecure flag| HTTP_MODE["HTTP mode<br/>No TLS<br/>Credentials exposed on wire"]

    DEFAULT --> CERT_VALID["Certificate validation<br/>verify=True (default)"]
    HTTP_MODE --> NO_CERT["No certificate validation<br/>verify=False<br/>Note: --insecure disables all security"]
    
    DEFAULT --> TIMEOUT_ISSUE["⚠ No timeout configured<br/>registryauth.py:116,118<br/>CWE-400: DoS via slow registry"]
```

---

## 6. Subprocess Security Model (Credential Helpers)

```mermaid
sequenceDiagram
    participant APP as regshape
    participant DCFG as docker config.json
    participant HELPER as docker-credential-{store}
    participant OS as Operating System

    APP->>DCFG: Read credHelpers map
    DCFG-->>APP: {"registry.io": "osxkeychain"}
    APP->>APP: Build helper name: "docker-credential-osxkeychain"
    Note over APP: PATH lookup — uses system PATH<br/>No absolute path forced
    APP->>OS: Popen(["docker-credential-osxkeychain", "get"], stdin=PIPE, stdout=PIPE)
    OS->>HELPER: Exec subprocess
    HELPER-->>APP: JSON {"Username": "user", "Secret": "pass"}
    APP->>APP: Parse credentials from stdout

    Note over APP,OS: Security consideration:<br/>If PATH is compromised (e.g., via env injection),<br/>a malicious binary named docker-credential-X<br/>could be executed. Mitigated by OS security controls.
```
