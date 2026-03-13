# Security Model Visual — Notation Project

**Generated**: 2026-03-12
All diagrams use Mermaid syntax.

---

## Diagram 1: Trust Boundary Map

```mermaid
graph TB
    subgraph UserBoundary["USER TRUST BOUNDARY (local machine)"]
        direction TB
        USER_ACT["User Actions\n(CLI invocation)"]
        LOCAL_CONFIG["Local Configuration\n~/.config/notation/\n(owned by user)"]
        TRUST_POLICY["Trust Policy JSON\n(policy-as-code)"]
        CRED_STORE["Credential Store\n(Docker credential helper)"]
        PLUGIN_BINARIES["Plugin Binaries\n(user-installed)"]
        NOTATION_BIN["notation binary\n(trusted application)"]
    end

    subgraph NetworkBoundary["NETWORK BOUNDARY (external — should be TLS)"]
        OCI_REGISTRY["OCI Registry\n(external service)"]
        TSA_SERVER["Timestamp Authority\n(external service)"]
    end

    subgraph PluginBoundary["PLUGIN SUBPROCESS BOUNDARY (isolated process)"]
        KEY_MATERIAL["Key Material\n(HSM / KMS / PKCS12)"]
        PLUGIN_PROCESS["Plugin Process\n(subprocess isolation)"]
    end

    USER_ACT -->|"invokes"| NOTATION_BIN
    NOTATION_BIN -->|"reads"| LOCAL_CONFIG
    LOCAL_CONFIG -->|"contains"| TRUST_POLICY
    LOCAL_CONFIG -->|"indexes"| PLUGIN_BINARIES
    NOTATION_BIN -->|"delegates credentials"| CRED_STORE
    NOTATION_BIN -->|"spawns subprocess"| PLUGIN_PROCESS
    PLUGIN_PROCESS -->|"accesses"| KEY_MATERIAL
    NOTATION_BIN -->|"TLS required"| OCI_REGISTRY
    NOTATION_BIN -->|"TLS required"| TSA_SERVER

    KEY_MATERIAL -.->|"NEVER CROSSES\nprocess boundary"| NOTATION_BIN

    style UserBoundary fill:#f0fdf4,stroke:#22c55e,stroke-width:2px
    style NetworkBoundary fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style PluginBoundary fill:#fce7f3,stroke:#ec4899,stroke-width:2px
    style KEY_MATERIAL fill:#fee2e2,stroke:#ef4444
```

---

## Diagram 2: Cryptographic Trust Chain

```mermaid
graph TD
    subgraph TrustAnchors["Trust Anchors\n(~/.config/notation/truststore/)"]
        ROOT_CA["Root CA Certificate\n(trust anchor — user-controlled)"]
        INTER_CA["Intermediate CA Certificate\n(optional)"]
        LEAF_CERT["Leaf / Signing Certificate\n(signer's identity)"]
    end

    subgraph Signature["Signature Envelope\n(stored in OCI Registry)"]
        ENV_CERT_CHAIN["Embedded Certificate Chain\n[leaf, intermediate, root]"]
        SIGNATURE_BYTES["Signature Bytes\n(ECDSA/RSA-PSS over payload)"]
        PAYLOAD["Payload\n{subject.digest, annotations}"]
        TIMESTAMP_CS["RFC 3161 Timestamp\n(optional countersignature)"]
    end

    subgraph Verification["Verification Steps (ordered)"]
        VERIFY1["1. Parse envelope\n(JWS or COSE)"]
        VERIFY2["2. Verify signature bytes\nagainst payload"]
        VERIFY3["3. Validate certificate chain\nagainst trust store"]
        VERIFY4["4. Match leaf cert identity\nagainst trust policy"]
        VERIFY5["5. Check cert revocation\n(if enforcement level)"]
        VERIFY6["6. Validate timestamp\n(if present)"]
        VERIFY7["7. Return outcome\n(allow / deny)"]
    end

    ROOT_CA -->|"signs"| INTER_CA
    INTER_CA -->|"signs"| LEAF_CERT
    LEAF_CERT -->|"embedded in"| ENV_CERT_CHAIN
    ENV_CERT_CHAIN -->|"used in"| VERIFY3
    SIGNATURE_BYTES -->|"verified in"| VERIFY2
    PAYLOAD -->|"digest matched in"| VERIFY2

    ROOT_CA -.->|"must be in\nnotation trust store"| VERIFY3

    VERIFY1 --> VERIFY2
    VERIFY2 --> VERIFY3
    VERIFY3 --> VERIFY4
    VERIFY4 --> VERIFY5
    VERIFY5 --> VERIFY6
    VERIFY6 --> VERIFY7

    style TrustAnchors fill:#dcfce7,stroke:#22c55e
    style Signature fill:#dbeafe,stroke:#3b82f6
    style Verification fill:#fef9c3,stroke:#eab308
```

---

## Diagram 3: Verification Levels and Outcomes

```mermaid
flowchart TD
    START["artifact reference provided\nnotation verify img:tag"]
    POLICY_LOOKUP["Look up trust policy scope\nfor registry + repository"]
    
    START --> POLICY_LOOKUP
    
    POLICY_LOOKUP --> LEVEL{verificationLevel?}

    LEVEL -->|"skip"| SKIP_RESULT["SKIP\nAll verification skipped\n(not recommended)"]
    
    LEVEL -->|"audit"| AUDIT_PATH["Run all checks\nLog failures\nDO NOT FAIL command"]
    AUDIT_PATH --> AUDIT_RESULT["AUDIT PASS\n(failures logged, not enforced)"]
    
    LEVEL -->|"permissive"| PERM_PATH["Run all checks\nFail only on certificate chain errors\nWarn on policy violations"]
    PERM_PATH --> PERM_RESULT["PERMISSIVE PASS / FAIL\nbased on cert chain only"]
    
    LEVEL -->|"strict (default)"| STRICT_PATH["Run all checks\nFail on ANY violation"]
    STRICT_PATH --> CERT_CHECK{cert chain\nvalid?}
    CERT_CHECK -->|"No"| STRICT_FAIL["FAIL ✗\nCertificate validation error"]
    CERT_CHECK -->|"Yes"| IDENTITY_CHECK{identity matches\ntrusted policy?}
    IDENTITY_CHECK -->|"No"| STRICT_FAIL2["FAIL ✗\nIdentity not trusted"]
    IDENTITY_CHECK -->|"Yes"| REVOKE_CHECK{revocation\ncheck passes?}
    REVOKE_CHECK -->|"No"| STRICT_FAIL3["FAIL ✗\nCertificate revoked"]
    REVOKE_CHECK -->|"Yes"| STRICT_PASS["PASS ✓\nSignature verified"]

    style SKIP_RESULT fill:#fef9c3,stroke:#eab308
    style AUDIT_RESULT fill:#fef9c3,stroke:#eab308
    style STRICT_PASS fill:#dcfce7,stroke:#22c55e
    style STRICT_FAIL fill:#fee2e2,stroke:#ef4444
    style STRICT_FAIL2 fill:#fee2e2,stroke:#ef4444
    style STRICT_FAIL3 fill:#fee2e2,stroke:#ef4444
```

---

## Diagram 4: Attack Surfaces and Mitigations

```mermaid
graph LR
    subgraph Attacks["Potential Attack Vectors"]
        A1["Forged Signature\nin OCI Registry"]
        A2["Malicious Plugin\nBinary"]
        A3["Trust Policy\nTampering"]
        A4["Certificate\nSubstitution"]
        A5["Dependency CVE\nin Go modules"]
        A6["Path Traversal\nin file operations"]
    end

    subgraph Mitigations["Mitigations"]
        M1["Cryptographic verification\n+ cert chain validation"]
        M2["Plugin subprocess\nisolation + user consent"]
        M3["JSON schema validation\n+ parse errors = abort"]
        M4["X.509 chain validation\nagainst trust anchors"]
        M5["govulncheck in CI\n0 CVEs confirmed"]
        M6["filepath.Clean()\n(recommended addition)"]
    end

    A1 -->|"blocked by"| M1
    A2 -->|"mitigated by"| M2
    A3 -->|"mitigated by"| M3
    A4 -->|"blocked by"| M4
    A5 -->|"monitored by"| M5
    A6 -->|"mitigated by"| M6

    style Attacks fill:#fee2e2,stroke:#ef4444
    style Mitigations fill:#dcfce7,stroke:#22c55e
```
