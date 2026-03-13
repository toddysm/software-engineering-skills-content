# Architecture Overview — Notation (Notary Project CLI)

**Analysis Date**: 2026-03-12  
**Repositories Analysed**: notation/v2, notation-go, notation-core-go, notation-plugin-framework-go

---

## What Is This System?

Notation is a CNCF Incubating project that provides a CLI tool and Go libraries for **signing and verifying OCI artifacts** (container images, Helm charts, etc.) and **arbitrary binary blobs**. It implements the [Notary Project specifications](https://github.com/notaryproject/specifications) and is designed to provide supply chain security for cloud-native workloads.

In simple terms: Notation is the `gpg`-equivalent for container images stored in OCI registries. You sign an image after building it, and verify the signature before deploying it.

---

## System Organisation — Four-Tier Layered Architecture

The system is split across four interconnected repositories, each occupying a distinct layer:

```
┌──────────────────────────────────────────────────────────────────┐
│ TIER 4 — CLI Layer (notation/v2)                                  │
│  User-facing commands: sign, verify, list, inspect, cert, plugin  │
│  Output formats: JSON / plain text / tree                         │
│  Registry interaction via oras-go/v2                              │
├──────────────────────────────────────────────────────────────────┤
│ TIER 3 — High-Level Library (notation-go)                         │
│  Signer/Verifier interfaces and implementations                   │
│  Trust policy and trust store management                          │
│  Plugin manager (subprocess-based CLI plugin protocol)            │
│  OCI registry repository abstraction                              │
├──────────────────────────────────────────────────────────────────┤
│ TIER 2 — Cryptographic Core (notation-core-go)                    │
│  Signature envelope formats: JWS (RFC 7515) and COSE (RFC 9052)  │
│  X.509 certificate chain validation                               │
│  Revocation checking: CRL and OCSP                                │
│  Timestamp countersignatures (RFC 3161 via tspclient-go)          │
├──────────────────────────────────────────────────────────────────┤
│ TIER 1 — Plugin Framework (notation-plugin-framework-go)          │
│  Plugin protocol contracts (JSON over stdin/stdout)               │
│  GenericPlugin / SignPlugin / VerifyPlugin interfaces             │
│  CLI runner for plugin authors                                    │
└──────────────────────────────────────────────────────────────────┘
```

**Key principle**: each tier depends only on lower tiers, never on higher ones. `notation-core-go` has no knowledge of CLI commands; the CLI has no knowledge of cryptographic internals.

---

## Component Guide

### The CLI (`notation/v2`)

The CLI is organised around [Cobra](https://github.com/spf13/cobra) commands. The top-level structure is:

```
notation
├── sign           — sign an OCI artifact (image/chart/etc.)
├── verify         — verify signatures on an OCI artifact
├── list (ls)      — list all signatures attached to an artifact
├── inspect        — show full details of a signature envelope
├── key            — manage local signing keys (add/list/set/delete)
├── cert           — manage trust store certificates
├── policy         — manage OCI trust policy
├── plugin         — install/list/uninstall signing plugins
├── blob           — sign/verify/inspect arbitrary files (not OCI)
│   └── policy     — manage blob trust policy
├── login          — log in to an OCI registry
├── logout         — log out of an OCI registry
└── version        — print version info
```

Each command offloads the actual work to `cmd/notation/internal/{sign,verify}/`, which orchestrates calls to `notation-go`.

The display subsystem (`cmd/notation/internal/display/`) supports three output renderers:
- **tree** (default): indented tree output for inspect/list
- **json**: machine-readable JSON
- **text**: minimal human-readable text for verify

### The Library (`notation-go`)

This is the public API that applications embed to add Notation signing/verification capabilities. The top-level `notation.go` file defines four interfaces:

- `Signer` — signs OCI artifacts
- `BlobSigner` — signs arbitrary data streams
- `Verifier` — verifies OCI artifacts against trust policy
- `BlobVerifier` — verifies blob signatures against trust policy

These are implemented in `signer/` and `verifier/`.

The **signer** package offers two implementations:
- `GenericSigner` — uses a local private key (PKCS#8, PEM)
- `PluginSigner` — delegates to a plugin binary via the plugin protocol

The **verifier** package implements multi-step verification:
1. Resolve the trust policy applicable to the artifact
2. Verify signature integrity (cryptographic verification)
3. Verify authenticity (certificate chain against trust store)
4. Check expiry
5. Optionally revoke-check via CRL/OCSP
6. Optionally delegate to a plugin for custom verification logic

The **trust policy** defines verification requirements per scope (registry+repository pattern). It supports three verification levels:
- `strict` — all five checks enforced
- `permissive` — all checks enforced but revocation errors are logged only
- `audit` — all issues logged, nothing blocked
- `skip` — no verification (useful for development)

### The Cryptographic Core (`notation-core-go`)

This layer handles the low-level signature format work:

- **Envelope registration**: JWS and COSE are registered as envelope types at package init time. New formats can be added without changing callers.
- **JWS format**: Encodes the signing payload as a JWT; the certificate chain is embedded in the `x5c` header as PEM-DER.
- **COSE format**: Uses CBOR encoding (via `go-cose` and `fxamacker/cbor`); more compact and appropriate for constrained environments.
- **Certificate chain validation**: Follows standard code-signing certificate profile rules plus Notary-specific requirements.
- **Revocation**: Uses the CDP (CRL Distribution Points) from certificates to fetch and cache CRLs; OCSP for online checking. Results are aggregated per certificate.
- **Timestamping**: Integrates with RFC 3161 TSAs (Time-Stamping Authorities) via `tspclient-go` to prove the signature existed at signing time even if the cert later expires.

### The Plugin Framework (`notation-plugin-framework-go`)

Notation supports a plugin model where third parties can integrate external key management systems (HSMs, cloud KMS like AWS KMS, Azure Key Vault, HashiCorp Vault).

The protocol is intentionally simple:
1. Notation discovers plugins in `~/.config/notation/plugins/<name>/notation-<name>` (libexec directory)
2. When signing, Notation invokes the plugin binary, writes a JSON request to its stdin, and reads the JSON response from stdout
3. Plugins implement one of three operations:
   - `GenerateSignature` — plugin holds the key, returns signature bytes
   - `GenerateEnvelope` — plugin returns the complete signed envelope
   - `VerifySignature` — plugin participates in verification (e.g., for proprietary trust)

This framework provides the Go types and the CLI dispatcher used by plugin authors. The two examples in `example/` show how to implement each mode.

---

## Data Flow: Signing an OCI Image

```
user: `notation sign my-registry.io/myapp:v1.0`
         |
         v
cmd/notation/sign.go
  → resolves key/plugin from config
  → constructs SignOptions{
      ArtifactReference, SignatureMediaType, Expiry, UserMetadata, Timestamper
    }
  → calls notation-go/Sign(ctx, repo, opts)
         |
         v
notation-go/notation.go: Sign()
  → resolves artifact reference via registry.Repository.Resolve()
  → calls signer.Sign(ctx, artifactDescriptor, signerOpts)
         |
         v (local key path)
signer/GenericSigner.Sign()
  → constructs signature.SignRequest{Payload, Signer, SigningScheme, ...}
  → calls signature.Sign(req)  [notation-core-go]
         |
         v
notation-core-go/signature: JWS or COSE Envelope.Sign(req)
  → computes payload hash
  → calls req.Signer.Sign(payloadBytes) → crypto/ecdsa or crypto/rsa
  → constructs envelope bytes
  → (optional) contacts TSA for timestamp countersignature
         |
         v
back in notation-go/notation.go
  → pushes signature blob to OCI registry via
    registry.Repository.PushSignature(ctx, mediaType, sigBlob, subject, annotations)
  → returns SignatureContent
         |
         v
cmd/notation/sign.go
  → prints success with signature digest
```

## Data Flow: Verifying an OCI Image

```
user: `notation verify my-registry.io/myapp@sha256:abc...`
         |
         v
cmd/notation/verify.go
  → loads trust policy, trust store
  → constructs VerifyOptions
  → calls notation-go/Verify(ctx, repo, opts)
         |
         v
notation-go/notation.go: Verify()
  → resolves artifact reference
  → calls repo.ListSignatures() to enumerate all attached signatures
  → for each signature:
      verifier.Verify(ctx, verifyOpts)
         |
         v
notation-go/verifier/verifier.go: Verify()
  1. Match artifact to trust policy scope
  2. Parse signature envelope (JWS or COSE)
  3. verify INTEGRITY: re-compute payload hash; validate envelope
  4. verify AUTHENTICITY: validate cert chain against trust store
     → notation-core-go/x509.ValidateCodeSigningCertChain()
  5. verify EXPIRY: check NotAfter / Expiry fields
  6. verify REVOCATION (if enforced):
     → notation-core-go/revocation: CRL or OCSP check per cert
  7. (if plugin configured) call PluginVerifier.VerifySignature()
         |
         v
  → returns VerificationOutcome{VerificationResults, EntityThatSigned}
         |
         v
cmd/notation/verify.go
  → display results via output renderer
  → exit 0 if all checks pass, exit 1 if any enforced check fails
```

---

## Configuration Layout

```
~/.config/notation/                   (overridable via NOTATION_CONFIG env)
├── config.json                        # global: insecure registries, cred store
├── signingkeys.json                   # named signing key to plugin mappings
├── trustpolicy.oci.json               # OCI artifact verification rules
├── trustpolicy.blob.json              # Blob verification rules
├── truststore/
│   └── x509/
│       ├── ca/                        # Trusted CA certificates
│       │   └── <store-name>/*.crt
│       └── signingAuthority/          # Code signing authority certs
│           └── <store-name>/*.crt
└── plugins/                           # Plugin binaries (in libexec)
    └── <plugin-name>/
        └── notation-<plugin-name>     # Executable plugin binary

~/.cache/notation/                     (overridable via NOTATION_CACHE)
└── crl/                               # CRL cache files (TTL-based)
    └── <url-hash>/

~/bin/notation                         # Installed CLI binary
```

---

## Technology Decisions

### Why Two Signature Formats (JWS and COSE)?

JWS/JWT is widely understood and has broad tooling support. COSE is the newer, CBOR-based standard better suited for embedded/IoT systems and produces smaller payloads. The Envelope abstraction allows both to be used interchangeably while keeping cryptographic details out of the higher layers.

### Why a Plugin Protocol over Embedded SDKs?

Security-sensitive key material should never leave a KMS/HSM boundary. Subprocess isolation means the plugin binary is a separate process — even if notation itself is compromised post-execution, the key material that passed through the plugin subprocess interface was only ever inside the plugin's memory. The JSON-over-stdin/stdout protocol is intentionally simple to audit and implement.

### Why oras-go/v2 for Registry Access?

`oras-go` (OCI Registry As Storage) provides a well-maintained, specification-compliant client for OCI distribution. Using the Referrers API (or fallback tag schema) to attach signatures as OCI artefacts to a subject follows the OCI v1.1 specification without requiring registry-specific extensions.

### Why Trust Policy Documents (not flags)?

Trust policy is security-critical configuration that should be version-controlled, auditable, and consistent across CI/CD pipelines. Encoding it as a checked-in JSON document (rather than command-line flags per verification) prevents accidental drift and supports GitOps workflows.

---

## Strengths of This Architecture

1. **Clean separation of concerns**: each layer has a single responsibility
2. **Interface-driven design**: callers depend on interfaces (Signer, Verifier, Repository, Envelope), not concrete types — enabling testing and extensibility
3. **Format agnosticism**: JWS and COSE both supported transparently through the Envelope registry pattern
4. **Security by design**: plugin subprocess isolation, trust policy as first-class config, certificate-chain validation, and revocation checking all built in
5. **Testability**: every layer has its own test suite; mock implementations provided in `internal/mock/`
6. **Supply chain security**: signed commits enforced in CI, OpenSSF scorecard evaluated, CodeQL analysis, SBOM-compatible design

---

## Cross-Cutting Concerns

- **Logging**: context-propagated Logger interface (matching logrus API) passed through all layers. CLI configures logrus; library code remains logging-framework agnostic.
- **Context propagation**: all APIs accept `context.Context` for cancellation, deadline, and trace propagation.
- **Error handling**: typed errors throughout; CLI maps them to appropriate exit codes in `cmd/notation/internal/errors/`.
- **Experimental features**: feature-flagged via `NOTATION_EXPERIMENTAL` environment variable; guarded at CLI flag parsing time.
