# Component Relationship Guide — Notation

**Analysis Date**: 2026-03-12

---

## At a Glance

This guide answers the question: *"If I want to work on X, what else will I need to look at?"*

---

## Central Components and Their Connections

### `notation-go/notation.go` — The Public API Contract

**What it is**: The `notation.go` file in the `notation-go` package root defines the four top-level interfaces: `Signer`, `BlobSigner`, `Verifier`, `BlobVerifier`. It also contains the top-level orchestration functions `Sign`, `SignBlob`, `Verify`, and `VerifyBlob`.

**What depends on it**:
- `notation/cmd/notation/internal/sign/sign.go` — calls `notation.Sign()` for OCI signing
- `notation/cmd/notation/internal/verify/verify.go` — calls `notation.Verify()` for OCI verification
- `notation/cmd/notation/blob/sign.go` — calls `notation.SignBlob()`
- `notation/cmd/notation/blob/verify.go` — calls `notation.VerifyBlob()`
- `notation/cmd/notation/list.go` — calls `notation.List()`

**What it depends on**:
- `notation-go/registry` — for OCI registry operations
- `notation-go/signer` — for signing implementations
- `notation-go/verifier` — for verification implementations
- `notation-core-go/signature` — for signing result types

---

### `notation-core-go/signature/envelope.go` — Signature Format Registry

**What it is**: The registry and factory for signature envelope types. JWS and COSE envelopes are registered here at package init time.

**What depends on it**:
- `notation-go/signer/signer.go` — calls `signature.NewEnvelope()` to create envelopes
- `notation-go/verifier/verifier.go` — calls `signature.ParseEnvelope()` to deserialise
- `notation-go/internal/envelope/envelope.go` — wraps envelope creation

**What it depends on**:
- `signature/jws` package — JWS implementation
- `signature/cose` package — COSE implementation
- `sync.Map` for thread-safe registration

**If you change it**: Any change to the `Envelope` interface breaks all envelope implementations (JWS and COSE). Any change to registration breaks `signer` and `verifier`. Changes must be backward-compatible.

---

### `notation-go/verifier/verifier.go` — Verification Orchestrator

**What it is**: The most complex component. Implements `notation.Verifier` by coordinating trust policy lookup, envelope parsing, certificate validation, revocation checking, and plugin verification.

**What depends on it**:
- `notation-go/notation.go` — used in `Verify()` and `VerifyBlob()`
- `notation/cmd/notation/internal/verify/verify.go` — constructs and uses verifier

**What it depends on**:
- `notation-go/verifier/trustpolicy` — trust policy lookup and validation level
- `notation-go/verifier/truststore` — certificate loading
- `notation-go/verifier/crl` — CRL-based revocation
- `notation-go/plugin` — plugin verification delegation
- `notation-core-go/signature` — envelope parsing
- `notation-core-go/x509` — certificate chain validation
- `notation-core-go/revocation` — OCSP and CRL revocation

**If you change it**: Affects the security assurance of the entire system. All five verification steps must remain. Tests in `verifier/verifier_test.go` and integration tests in `test/e2e/` should be run.

---

### `notation-go/verifier/trustpolicy/trustpolicy.go` — Trust Policy Engine

**What it is**: Loads and validates the OCI/Blob trust policy documents (`trustpolicy.oci.json`, `trustpolicy.blob.json`). Determines which trust policy scope matches a given artifact reference and what verification actions to apply.

**What depends on it**:
- `notation-go/verifier/verifier.go` — loads and applies trust policy
- `notation/cmd/notation/internal/verify/verify.go` — constructs trust policy document
- `notation/cmd/notation/policy/` commands — show/import trust policy

**What it depends on**:
- `notation-go/verifier/truststore` — loads certificates referenced by policy
- `notation-go/dir` — locates policy file paths

---

### `notation-go/signer/signer.go` — Signing Implementations

**What it is**: `GenericSigner` (local key) and `PluginSigner` (remote key via plugin). Both implement `notation.Signer` and `notation.BlobSigner`.

**What depends on it**:
- `notation-go/notation.go` — used in `Sign()` and `SignBlob()`
- `notation/cmd/notation/internal/sign/sign.go` — constructs appropriate signer

**What it depends on**:
- `notation-core-go/signature` — to create signed envelopes
- `notation-plugin-framework-go/plugin` — plugin protocol types
- `notation-go/plugin` — plugin manager for subprocess invocation

---

### `notation-go/plugin/plugin.go` — Plugin Subprocess Manager

**What it is**: `CLIPlugin` wraps a plugin binary. It discovers plugins from the libexec directory, launches them as subprocesses, and communicates via JSON stdin/stdout.

**What depends on it**:
- `notation-go/signer/plugin.go` — uses CLIPlugin for PluginSigner
- `notation-go/verifier/verifier.go` — uses CLIPlugin for PluginVerifier
- `notation/cmd/notation/plugin/` commands — installs/uninstalls plugins

**What it depends on**:
- `notation-go/dir` — locates plugin binary paths
- `notation-plugin-framework-go/plugin` — protocol types and error codes
- `os/exec` (stdlib) — subprocess execution
- `notation-go/internal/semver` — plugin version compatibility

---

### `notation-go/registry/repository.go` — OCI Registry Client

**What it is**: Implements `notation.Repository` using `oras-go/v2`. Handles resolving artifact references, listing signatures via the OCI Referrers API (with fallback to tag schema), fetching signature blobs, and pushing new signatures.

**What depends on it**:
- `notation-go/notation.go` — used in all `Sign/Verify/List` operations

**What it depends on**:
- `oras.land/oras-go/v2` — OCI client
- `github.com/opencontainers/image-spec` — OCI descriptor types

---

### `notation-core-go/x509/cert.go` — Certificate Chain Validator

**What it is**: `ValidateCodeSigningCertChain()` performs the complete X.509 certificate chain validation per the Notary code signing certificate profile: root trust, intermediate validity, EKU (Extended Key Usage), key usage, and Notary-specific profile constraints.

**What depends on it**:
- `notation-go/verifier/verifier.go` — called during authenticity check
- `notation-go/verifier/truststore` — used alongside cert loading

---

### `notation/internal/osutil/file.go` — File System Utilities

**What it is**: Utility functions for reading/writing files with specific permissions, copying files, computing SHA-256 checksums, and detecting content types.

**What depends on it**:
- `notation/cmd/notation/plugin/install.go` — copies plugin binary, validates checksum
- `notation/cmd/notation/cert/add.go` — copies certificate files into trust store
- `notation/cmd/notation/internal/sign/sign.go` — reads key files
- `notation/cmd/notation/internal/truststore/truststore.go` — reads cert files

---

## Package Responsibility Summary

| Package | Responsibility | Layer |
|---------|---------------|-------|
| `cmd/notation` | User interface, cobra commands, flag parsing | CLI |
| `cmd/notation/internal/sign` | Sign orchestration: key/plugin resolution → notation-go | CLI internal |
| `cmd/notation/internal/verify` | Verify orchestration: policy/store setup → notation-go | CLI internal |
| `cmd/notation/internal/display` | Multi-format output renderer (json/text/tree) | CLI internal |
| `notation-go/notation` | Public API: Sign/Verify/List interfaces and functions | Library |
| `notation-go/signer` | Local and plugin-based signing implementations | Library |
| `notation-go/verifier` | Full verification workflow with policy enforcement | Library |
| `notation-go/verifier/trustpolicy` | Trust policy document parsing and matching | Library |
| `notation-go/verifier/truststore` | Certificate loading from trust store | Library |
| `notation-go/registry` | OCI registry operations adapter | Library |
| `notation-go/plugin` | Plugin subprocess discovery and execution | Library |
| `notation-go/config` | Configuration file (config.json, signingkeys.json) I/O | Library |
| `notation-go/dir` | Canonical config/cache/libexec path definitions | Library |
| `notation-core-go/signature` | Signature envelope: JWS and COSE format implementations | Core |
| `notation-core-go/x509` | X.509 certificate chain validation | Core |
| `notation-core-go/revocation` | CRL and OCSP revocation checking | Core |
| `notation-plugin-framework-go/plugin` | Plugin protocol types and CLI dispatcher | Framework |

---

## Impact Analysis: What Changes If I Modify...

### `notation-core-go/signature/types.go` (SignRequest, SignedAttributes)
**Affected**: `signature/jws`, `signature/cose`, `notation-go/signer`, `notation-go/verifier`, and all callers. **High blast radius** — these are the shared data structures for the entire signing pathway.

### `notation-go/verifier/trustpolicy/trustpolicy.go` (trust policy schema)
**Affected**: `notation-go/verifier`, `notation/cmd/notation/internal/verify`, `notation/cmd/notation/policy/*`. Also affects user-authored policy JSON files. **Breaking changes require migration guidance**.

### `notation-plugin-framework-go/plugin/plugin.go` (Plugin interfaces)
**Affected**: All existing plugins in the ecosystem (third-party KMS plugins). **Interface changes are breaking for plugin authors** — requires major version bump.

### `notation-go/plugin/plugin.go` (plugin subprocess protocol)
**Affected**: `signer/plugin.go`, `verifier/verifier.go`. Protocol changes must maintain backward compatibility with published plugin binaries.

### `notation/cmd/notation/internal/sign/sign.go`
**Affected**: Only the `sign` command output. Lowest blast radius — well-isolated.

### `notation-go/log/log.go` (Logger interface)
**Affected**: All packages that accept a logger via context. In practice, low impact as all implementations (logrus) conform automatically.
