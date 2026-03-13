# Dependency Graphs — Notation Project

**Generated**: 2026-03-12
All diagrams use Mermaid syntax.

---

## Graph 1: Repository-Level Dependency Graph

```mermaid
graph LR
    NOT["notation\ngithub.com/notaryproject/notation/v2\nGo 1.24.0\nCLI Binary"]
    NOTGO["notation-go\ngithub.com/notaryproject/notation-go\nGo 1.23.0\nHigh-level Library"]
    NOTCORE["notation-core-go\ngithub.com/notaryproject/notation-core-go\nGo 1.23.0\nCrypto Core"]
    NOTFW["notation-plugin-framework-go\ngithub.com/notaryproject/notation-plugin-framework-go\nGo 1.20\nPlugin SDK"]

    NOT -->|"imports"| NOTGO
    NOT -->|"imports"| NOTCORE
    NOT -->|"imports"| NOTFW
    NOTGO -->|"imports"| NOTCORE
    NOTGO -->|"imports"| NOTFW
    NOTCORE -.->|"no dep on"| NOTGO
    NOTCORE -.->|"no dep on"| NOTFW
    NOTFW -.->|"no dep on"| NOTCORE
    NOTFW -.->|"no dep on"| NOTGO

    style NOT fill:#dbeafe,stroke:#1d4ed8,color:#1e3a5f,font-weight:bold
    style NOTGO fill:#dcfce7,stroke:#15803d,color:#14532d,font-weight:bold
    style NOTCORE fill:#fef9c3,stroke:#ca8a04,color:#713f12,font-weight:bold
    style NOTFW fill:#fce7f3,stroke:#a21caf,color:#4a044e,font-weight:bold
```

---

## Graph 2: Key Package-Level Dependencies (Main Module)

```mermaid
graph TB
    subgraph CMD["cmd/notation/"]
        MAIN2[main.go]
        SIGN2[sign.go]
        VERIFY2[verify.go]
        BLOB2[blob/]
        POLICY2[policy/]
        KEY2[key/]
        CERT2[cert/]
        PLUGIN2[plugin/]
        LOGIN2[login.go]
        TAG2[tag.go]
        LIST2[list.go]
        INSPECT2[inspect.go]
    end

    subgraph INTERNAL["cmd/notation/internal/"]
        OSUTIL[osutil/\nfile helpers]
        IKEY[key/\nkeystore]
        ICERT[truststore/\ncert store]
        IPLUGIN[plugin/\nupdate/install]
        IEXPER[experimental/\nfeature flags]
        IREGISTRY[httputil/\nregistry helpers]
    end

    subgraph DEPNOTGO["notation-go (external module)"]
        SIGNER_IMPL[signer.go\nSigner impl]
        VERIFIER_IMPL[verifier.go\nVerifier impl]
        PLUGIN_MGR[plugin/manager.go]
        DIR_PKG[dir/\npath constants]
        TRUSTPOL[verifier/trustpolicy/]
        REG_CLIENT[registry/\noras wrapper]
    end

    MAIN2 --> SIGN2
    MAIN2 --> VERIFY2
    MAIN2 --> BLOB2
    MAIN2 --> POLICY2
    MAIN2 --> KEY2
    MAIN2 --> CERT2
    MAIN2 --> PLUGIN2
    MAIN2 --> LOGIN2
    MAIN2 --> TAG2
    MAIN2 --> LIST2
    MAIN2 --> INSPECT2

    SIGN2 --> SIGNER_IMPL
    VERIFY2 --> VERIFIER_IMPL
    VERIFY2 --> TRUSTPOL
    KEY2 --> IKEY
    CERT2 --> ICERT
    PLUGIN2 --> IPLUGIN
    IKEY --> DIR_PKG
    ICERT --> DIR_PKG
    IPLUGIN --> OSUTIL
    IPLUGIN --> PLUGIN_MGR
    SIGN2 --> IREGISTRY
    VERIFY2 --> IREGISTRY
    IREGISTRY --> REG_CLIENT

    style CMD fill:#dbeafe,stroke:#3b82f6
    style INTERNAL fill:#eff6ff,stroke:#93c5fd
    style DEPNOTGO fill:#dcfce7,stroke:#22c55e
```

---

## Graph 3: Critical Path for Signing

```mermaid
graph LR
    SIGN_CMD2["sign.go\nrunSign()"] -->|"notation.Sign()"| SIGNER_RESOLVE["signer.go\nResolveKey()"]
    SIGNER_RESOLVE -->|"load key"| KEY_STORE["signingkeys.json\n+ notation-go/dir"]
    SIGNER_RESOLVE -->|"invoke plugin"| PLUGIN_EXEC["plugin/manager.go\nExec()"]
    PLUGIN_EXEC -->|"subprocess"| PLUGIN_BIN3["~/.config/notation/\nplugins/<name>"]

    SIGN_CMD2 -->|"notation.Sign()"| ENVELOPE_SIGN["notation-core-go\nEnvelope.Sign()"]
    ENVELOPE_SIGN -->|"algo choice"| JWS_OR_COSE["jws.Envelope or\ncose.Envelope"]
    
    SIGN_CMD2 -->|"oras-go"| REGISTRY_PUSH["notation-go/registry\nPushSignature()"]
    REGISTRY_PUSH -->|"OCI Referrers API"| OCI_REG2["OCI Registry\n(network)"]

    style SIGN_CMD2 fill:#dbeafe,stroke:#3b82f6
    style PLUGIN_BIN3 fill:#fce7f3,stroke:#ec4899
    style OCI_REG2 fill:#f3f4f6,stroke:#9ca3af
```

---

## Graph 4: Critical Path for Verification

```mermaid
graph LR
    VERIFY_CMD2["verify.go\nrunVerify()"] -->|"load policy"| TRUST_POL2["notation-go/verifier\ntrust policy parse + validate"]
    VERIFY_CMD2 -->|"notation.Verify()"| VERIFIER_IMPL2["notation-go\nverifier.Verify()"]

    VERIFIER_IMPL2 -->|"fetch signatures"| REG_LIST["registry/oras.go\nListSignatures()"]
    REG_LIST -->|"OCI Referrers API"| OCI_REG3["OCI Registry\n(network)"]
    OCI_REG3 -->|"sig manifest"| SIG_FETCH["registry/oras.go\nFetchSignatureBlob()"]
    SIG_FETCH --> ENVELOPE_PARSE["notation-core-go\nEnvelope.Verify()"]
    ENVELOPE_PARSE --> X509_CHK["x509/\nVerifier.Verify()\ncert chain check"]
    X509_CHK --> TRUST_POL2

    TRUST_POL2 -->|"trusted identities"| DN_MATCH["trustpolicy\nDN matching\n(go-ldap/v3)"]
    DN_MATCH -->|"allow/deny"| OUTCOME["VerificationOutcome\n{ success, signerInfo }"]

    style VERIFY_CMD2 fill:#dcfce7,stroke:#22c55e
    style OCI_REG3 fill:#f3f4f6,stroke:#9ca3af
    style OUTCOME fill:#fef9c3,stroke:#eab308
```

---

## Graph 5: External Dependency Web (Third-Party Packages)

```mermaid
graph TB
    subgraph NOTCORE2["notation-core-go"]
        C_JWT["golang-jwt/jwt/v4\nJWS envelope parsing"]
        C_COSE["veraison/go-cose\nCOSE envelope"]
        C_CBOR["fxamacker/cbor/v2\nCBOR encoding"]
        C_CRYPTO["golang.org/x/crypto\nextended crypto"]
        C_TSP_CORE["notaryproject/tspclient-go\nRFC 3161"]
    end

    subgraph NOTGO2["notation-go"]
        G_ORAS["oras.land/oras-go/v2\nOCI client"]
        G_OCI_SPEC["opencontainers/image-spec\nOCI types"]
        G_LDAP["go-ldap/ldap/v3\nDN parsing"]
        G_TSP["notaryproject/tspclient-go\nRFC 3161"]
    end

    subgraph MAINREPO["notation main"]
        M_COBRA["spf13/cobra\nCLI framework"]
        M_LOGRUS["sirupsen/logrus\nlogging"]
        M_TERM["golang.org/x/term\nterminal control"]
    end

    C_JWT --> JWS_ENVELOPE["JWS envelope\nconstruction/parsing"]
    C_COSE --> COSE_ENVELOPE["COSE envelope\nconstruction/parsing"]
    C_CBOR --> COSE_ENVELOPE
    C_CRYPTO --> COSE_ENVELOPE
    C_TSP_CORE --> TIMESTAMP["RFC 3161\nTimestamping"]
    G_TSP --> TIMESTAMP
    G_ORAS --> OCI_OPS["OCI registry\noperations"]
    G_OCI_SPEC --> OCI_OPS
    G_LDAP --> DN_PARSE["Distinguished Name\nparsing"]
    M_COBRA --> CLI_FRAMEWORK["CLI command\nstructure"]
    M_LOGRUS --> CONTEXT_LOG["Context-based\nlogging"]
    M_TERM --> TERMINAL_IO["Terminal\npassword input"]
```
