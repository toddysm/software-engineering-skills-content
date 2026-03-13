# Detailed Architecture Diagrams — Notation Project

**Generated**: 2026-03-12

All diagrams use [Mermaid](https://mermaid.js.org/) syntax and can be rendered in:
- GitHub Markdown (native support)
- VS Code with the Mermaid Preview extension
- Any Mermaid-compatible viewer at https://mermaid.live

---

## Diagram 1: Four-Tier Component Architecture

```mermaid
graph TB
    subgraph CLI["Tier 1 — CLI Binary (notation)"]
        MAIN[main.go\nCLI entrypoint]
        SIGN_CMD[sign command]
        VERIFY_CMD[verify command]
        POLICY_CMD[policy command]
        KEY_CMD[key command]
        CERT_CMD[cert command]
        PLUGIN_CMD[plugin command]
        BLOB_CMD[blob sign/verify]
        LOGIN_CMD[login command]
    end

    subgraph LIB["Tier 2 — Library (notation-go)"]
        SIGNER[notation.Signer\ninterface]
        VERIFIER[notation.Verifier\ninterface]
        REGISTRY_IF[registry.Repository\ninterface]
        TRUSTPOLICY[trustpolicy\nvalidation]
        LOG[log\ncontext-based logger]
    end

    subgraph CORE["Tier 3 — Core (notation-core-go)"]
        ENVELOPE_IF[signature.Envelope\ninterface]
        JWS[jws.Envelope\nimplementation]
        COSE[cose.Envelope\nimplementation]
        X509_VERIFY[x509\ncert chain verifier]
        TSP[tspclient\nRFC 3161 timestamp]
    end

    subgraph FRAMEWORK["Tier 4 — Plugin Framework (notation-plugin-framework-go)"]
        PLUGIN_IF[plugin.Plugin\ninterface]
        PLUGIN_RUNNER[plugin subprocess\njson stdin/stdout]
        SIGN_PLUGIN[SignPlugin\ninterface]
        VERIFY_PLUGIN[VerifyPlugin\ninterface]
    end

    subgraph EXTERNAL["External Systems"]
        OCI_REG[(OCI Registry\nDocker Hub / GHCR / ACR)]
        PLUGIN_BIN[Plugin Binaries\n~/.config/notation/plugins/]
        TSA[Timestamp Authority\nRFC 3161 HTTPS]
        CRED_HELPER[Docker Credential\nHelper]
    end

    MAIN --> SIGN_CMD
    MAIN --> VERIFY_CMD
    MAIN --> POLICY_CMD
    MAIN --> KEY_CMD
    MAIN --> CERT_CMD
    MAIN --> PLUGIN_CMD
    MAIN --> BLOB_CMD
    MAIN --> LOGIN_CMD

    SIGN_CMD --> SIGNER
    VERIFY_CMD --> VERIFIER
    BLOB_CMD --> SIGNER
    BLOB_CMD --> VERIFIER

    SIGNER --> REGISTRY_IF
    VERIFIER --> REGISTRY_IF
    SIGNER --> ENVELOPE_IF
    VERIFIER --> ENVELOPE_IF
    VERIFIER --> TRUSTPOLICY

    ENVELOPE_IF --> JWS
    ENVELOPE_IF --> COSE
    JWS --> X509_VERIFY
    COSE --> X509_VERIFY
    JWS --> TSP
    COSE --> TSP

    SIGNER --> PLUGIN_IF
    PLUGIN_IF --> PLUGIN_RUNNER
    SIGN_PLUGIN --> PLUGIN_RUNNER
    VERIFY_PLUGIN --> PLUGIN_RUNNER

    REGISTRY_IF --> OCI_REG
    PLUGIN_RUNNER --> PLUGIN_BIN
    TSP --> TSA
    LOGIN_CMD --> CRED_HELPER

    style CLI fill:#dbeafe,stroke:#3b82f6
    style LIB fill:#dcfce7,stroke:#22c55e
    style CORE fill:#fef9c3,stroke:#eab308
    style FRAMEWORK fill:#fce7f3,stroke:#ec4899
    style EXTERNAL fill:#f3f4f6,stroke:#9ca3af
```

---

## Diagram 2: Signing Data Flow (Sequence)

```mermaid
sequenceDiagram
    actor User
    participant CLI as notation CLI
    participant NotGo as notation-go<br/>Signer
    participant Core as notation-core-go<br/>Envelope
    participant Plugin as Plugin Binary<br/>(subprocess)
    participant Registry as OCI Registry
    participant TSA as Timestamp Authority

    User->>CLI: notation sign registry.example.com/app:v1.0

    CLI->>Registry: Resolve reference → get artifact descriptor
    Registry-->>CLI: { digest: sha256:abc..., mediaType, size }

    CLI->>NotGo: Sign(ctx, descriptor, SignOptions)

    NotGo->>Core: newEnvelope(JWS or COSE)
    Core-->>NotGo: empty envelope

    NotGo->>Plugin: GenerateSignature request<br/>{ keyId, hash: sha256(payload), algorithm }
    Note over Plugin: Plugin accesses key<br/>(HSM / KMS / PKCS12)
    Plugin-->>NotGo: { signature, signingCertChain }

    NotGo->>Core: Sign(SignRequest)<br/>{ payload, signerInfo, annotations }
    Core-->>NotGo: envelope bytes (JWS or COSE)

    alt --timestamp-url provided
        NotGo->>TSA: timestamp(signatureValue)
        TSA-->>NotGo: RFC 3161 countersignature
        NotGo->>Core: embed timestamp in envelope
    end

    NotGo-->>CLI: signatureEnvelope, signerInfo

    CLI->>Registry: Push signature manifest<br/>{ subject: descriptor, envelope, mediaType }
    Registry-->>CLI: signature manifest digest

    CLI-->>User: Successfully signed registry.example.com/app:v1.0
```

---

## Diagram 3: Verification Data Flow (Sequence)

```mermaid
sequenceDiagram
    actor User
    participant CLI as notation CLI
    participant NotGo as notation-go<br/>Verifier
    participant Policy as trustpolicy<br/>validator
    participant Core as notation-core-go<br/>Envelope
    participant Registry as OCI Registry
    participant X509 as x509<br/>chain verifier

    User->>CLI: notation verify registry.example.com/app:v1.0

    CLI->>Registry: Resolve reference → artifact descriptor
    Registry-->>CLI: { digest: sha256:abc..., mediaType }

    CLI->>Policy: Load & validate trust policy for registry.example.com/app
    Policy-->>CLI: applicable policy (scope, trusted identities, verification level)

    CLI->>NotGo: Verify(ctx, VerifyOptions)

    NotGo->>Registry: ListSignatures for artifact digest
    Registry-->>NotGo: [ signatureManifest1, signatureManifest2 ]

    loop For each signature
        NotGo->>Registry: FetchSignatureBlob(signatureManifest)
        Registry-->>NotGo: envelopeBytes, mediaType

        NotGo->>Core: ParseEnvelope(envelopeBytes)
        Core-->>NotGo: EnvelopeContent { payload, signerInfo }

        Note over NotGo: Validate payload.subject.digest<br/>matches artifact digest

        NotGo->>X509: VerifyCertChain(signerInfo.CertChain, trustAnchors)
        X509-->>NotGo: verified leaf cert

        Note over NotGo: Match leaf cert subject<br/>against trusted identities in policy

        alt Timestamp present in envelope
            Note over NotGo: Validate RFC 3161 timestamp<br/>against TSA trust store
            Note over NotGo: Use signing time for<br/>cert expiry check
        else No timestamp
            Note over NotGo: Use current time for<br/>cert expiry check
        end

        NotGo->>NotGo: Check revocation policy<br/>(enforce / audit / skip)
    end

    NotGo-->>CLI: VerificationOutcome { success, signerInfo, annotations }
    CLI-->>User: Successfully verified registry.example.com/app:v1.0
```

---

## Diagram 4: Plugin Architecture

```mermaid
graph LR
    subgraph Process1["notation Process (PID 1234)"]
        NOTATION[notation binary]
        PM[plugin.Manager]
        PR[plugin.Runner]
        STDIN_WRITE[JSON request\nstdin write]
        STDOUT_READ[JSON response\nstdout read]
    end

    subgraph Process2["Plugin Process (PID 5678)"]
        PLUGIN_EXE[notation-myplugin binary]
        DISPATCHER[plugin.Dispatch]
        HANDLER[SignPlugin / VerifyPlugin\nimplementation]
        KMS[Key Material\n(HSM / KMS / PKCS12)]
    end

    NOTATION -->|1. resolve plugin name| PM
    PM -->|2. locate binary in libexec dir| PR
    PR -->|3. os.exec.Start| PLUGIN_EXE
    PR --> STDIN_WRITE
    STDIN_WRITE -->|4. JSON SignatureRequest\nvia stdin| DISPATCHER
    DISPATCHER -->|5. dispatch by operation| HANDLER
    HANDLER <-->|6. access key material\n(never leaves plugin)| KMS
    HANDLER -->|7. return signature bytes| DISPATCHER
    DISPATCHER -->|8. JSON SignatureResponse\nvia stdout| STDOUT_READ
    STDOUT_READ -->|9. parse response| NOTATION

    style Process1 fill:#dbeafe,stroke:#3b82f6
    style Process2 fill:#dcfce7,stroke:#22c55e
    style KMS fill:#fce7f3,stroke:#ec4899
```

---

## Diagram 5: Trust Model and Configuration Layout

```mermaid
graph TD
    subgraph UserConfig["~/.config/notation/ (User Configuration Root)"]
        TP[trustpolicy.oci.json\nor trustpolicy.blob.json]
        SK[signingkeys.json\nkey aliases → plugin/keyId]
        
        subgraph TrustStore["truststore/\nx509/"]
            CA_DIR["ca/\n<named-store>/\n*.pem (trust anchors)"]
            SIGNINGAUTH_DIR["signingAuthority/\n<named-store>/\n*.pem"]
            TSA_DIR["tsa/\n<named-store>/\n*.pem (TSA trust anchors)"]
        end

        subgraph Plugins["plugins/\n<plugin-name>/"]
            PLUGIN_BIN2["notation-<plugin-name>\n(binary)"]
        end
    end

    subgraph TrustPolicy["Trust Policy Resolution"]
        TP -->|"registryScopes:\n- registry.example.com/app"| SCOPE
        TP -->|"signatureVerification:\nlevel: strict"| VER_LEVEL
        TP -->|"trustStores:\n- ca:mystore"| STORE_REF
        TP -->|"trustedIdentities:\n- x509/cn:signer@example.com"| IDENTITY
    end

    subgraph VerificationChain["Verification Chain"]
        SCOPE --> SCOPE_MATCH{scope matches\nartifact reference?}
        SCOPE_MATCH -->|Yes| STORE_REF
        STORE_REF --> CA_DIR
        CA_DIR -->|trust anchors| CERT_VERIFY[X.509 cert chain\nverification]
        CERT_VERIFY -->|verified leaf cert| IDENTITY
        IDENTITY -->|DN matching| RESULT{ACCEPT ✓\nor REJECT ✗}
    end

    style UserConfig fill:#f0fdf4,stroke:#22c55e
    style TrustPolicy fill:#eff6ff,stroke:#3b82f6
    style VerificationChain fill:#fefce8,stroke:#eab308
```

---

## Diagram 6: OCI Referrers Model (How Signatures Are Stored)

```mermaid
graph LR
    subgraph Registry["OCI Registry"]
        SUBJECT_MANIFEST["Image Manifest\napp:v1.0\ndigest: sha256:abc..."]
        
        SIG1["Signature Manifest 1\nmediaType: application/vnd.cncf.notary.v2.signature\nsubject: sha256:abc...\nenvelopeMediaType: application/jose+json"]
        
        SIG2["Signature Manifest 2\nmediaType: application/vnd.cncf.notary.v2.signature\nsubject: sha256:abc...\nenvelopeMediaType: application/cose"]

        BLOB1["Signature Blob\n(JWS envelope bytes)"]
        BLOB2["Signature Blob\n(COSE envelope bytes)"]

        REFERRERS_LIST["Referrers Index\nsha256:abc... →\n[SigManifest1, SigManifest2]"]
    end

    SUBJECT_MANIFEST -->|"referenced by 'subject' field"| SIG1
    SUBJECT_MANIFEST -->|"referenced by 'subject' field"| SIG2
    SIG1 -->|"OCI layer"| BLOB1
    SIG2 -->|"OCI layer"| BLOB2
    REFERRERS_LIST -->|"indexes"| SIG1
    REFERRERS_LIST -->|"indexes"| SIG2

    style SUBJECT_MANIFEST fill:#dbeafe,stroke:#3b82f6
    style SIG1 fill:#dcfce7,stroke:#22c55e
    style SIG2 fill:#dcfce7,stroke:#22c55e
    style BLOB1 fill:#fef9c3,stroke:#eab308
    style BLOB2 fill:#fef9c3,stroke:#eab308
    style REFERRERS_LIST fill:#fce7f3,stroke:#ec4899
```

---

## Diagram 7: Envelope Package Selection (JWS vs COSE)

```mermaid
flowchart TD
    USER_INPUT[User passes\n--signature-format flag]
    DEFAULT[Default:\njws]

    USER_INPUT --> FORMAT_CHECK{format?}
    DEFAULT --> FORMAT_CHECK

    FORMAT_CHECK -->|"jws"| JWS_PKG["notation-core-go/\ninternal/envelope/jws\n\nOutput: application/jose+json"]
    FORMAT_CHECK -->|"cose"| COSE_PKG["notation-core-go/\ninternal/envelope/cose\n\nOutput: application/cose"]

    JWS_PKG --> REGISTRY_BOTH["Stored in OCI Registry\nas signature manifest layer"]
    COSE_PKG --> REGISTRY_BOTH

    REGISTRY_BOTH --> VERIFY_DISPATCH["On verify:\nRegisterEnvelopeType registry\ndispatches by mediaType"]
    VERIFY_DISPATCH --> JWS_PKG
    VERIFY_DISPATCH --> COSE_PKG

    style JWS_PKG fill:#dbeafe,stroke:#3b82f6
    style COSE_PKG fill:#dcfce7,stroke:#22c55e
```
