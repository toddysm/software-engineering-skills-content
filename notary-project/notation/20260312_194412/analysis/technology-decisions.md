# Technology Decisions — Notation

**Analysis Date**: 2026-03-12

---

## Why Go?

The entire Notary Project toolchain is written in Go. Key reasons observable from the codebase:
- **Crypto standard library**: Go's `crypto/x509`, `crypto/tls`, `crypto/ecdsa`, and `crypto/rsa` packages are carefully maintained and audited. Using the standard library reduces risk versus custom crypto implementations.
- **Single binary distribution**: Go compiles to a statically linked binary per platform — critical for a security tool installed in CI/CD environments with no dependency on system libraries.
- **Subprocess model**: Go's `os/exec` package enables the clean plugin subprocess model.
- **Module system**: Go modules enable the strict versioned dependency tree necessary for a security-critical supply chain tool.

---

## Why Two Signature Formats (JWS and COSE)?

**Decision**: Support both JSON Web Signatures (`application/jose+json`) and CBOR Object Signing and Encryption (`application/cose`).

**Reasoning visible from code**:
- The `Envelope` interface in `notation-core-go/signature/envelope.go` uses a **registry pattern** — formats are registered at init time, allowing new formats without touching callers.
- JWS/JWT is the incumbent format with the widest tooling ecosystem; COSE is the IETF successor with a more compact binary encoding.
- The user chooses via `--signature-format {jws|cose}` flag; JWS is the default.
- `RegisteredEnvelopeTypes()` makes the supported formats introspectable.

**Implication**: Adding a third format (e.g., if a future spec mandates one) requires only adding a new package implementing `Envelope` and calling `RegisterEnvelopeType()` at init.

---

## Why oras-go/v2 for Registry Access?

**Decision**: Use `oras.land/oras-go/v2` instead of writing raw OCI distribution API calls.

**Reasoning**:
- `oras-go` is the reference Go client for OCI distribution protocol — it handles Referrers API, fallback tag schema, content negotiation, and authentication.
- The `Repository` interface in `notation-go/registry/interface.go` wraps only four operations (`Resolve`, `ListSignatures`, `FetchSignatureBlob`, `PushSignature`), keeping the surface area small and the OCI implementation swappable.
- Notation stores signatures as OCI artefacts referencing their subject (via `subject` field in OCI manifest) rather than modifying the tagged manifest — this is the OCI v1.1 Referrers model.

---

## Why Trust Policy as a JSON File?

**Decision**: Trust policy is a checked-in JSON file (`trustpolicy.oci.json`), not CLI flags.

**Reasoning**:
- A JSON file can be committed to a Git repository alongside application code, enabling policy-as-code and GitOps review workflows.
- The same policy document can be distributed to all engineers and CI systems, ensuring consistent verification behaviour.
- The validation logic in `notation-go/verifier/trustpolicy/` can be tested independently of the CLI.
- The file supports structured wildcards (`registries.example.com/*`), version ranges, and per-scope verification levels.

---

## Why the Plugin Subprocess Protocol?

**Decision**: Plugins are separate binaries invoked as subprocesses; communication is JSON over stdin/stdout.

**Reasoning visible from code**:
- **Security isolation**: The key material (private key bytes, HSM handles) never leaves the plugin process. Even if the `notation` binary were compromised in memory, the key is inaccessible.
- **Language agnosticism**: Plugin authors can use any language that can read stdin and write stdout. The framework (`notation-plugin-framework-go`) provides a Go SDK, but other languages work too.
- **Low IPC complexity**: stdin/stdout is universally available; no sockets, no shared memory, no RPC framework to audit.
- **Discoverability**: Plugins are discovered by scanning the libexec directory (`~/.config/notation/plugins/`), following the naming convention `notation-<plugin-name>`.

The `plugin/manager_unix.go` and `plugin/manager_windows.go` split shows platform-specific binary discovery while keeping the protocol layer unified.

---

## Why Separate Packages for OCI vs Blob Trust Policy?

**Decision**: `verifier/trustpolicy` has separate `oci.go` and `blob.go` with separate JSON documents.

**Reasoning**:
- OCI artifact verification requires resolving registry references, listing signatures by Referrers API, and matching against registry+repository-based scopes.
- Blob verification deals with local files and detached signature files with no registry involvement.
- The two use-cases have different trust scope concepts: OCI uses registry paths; blobs use arbitrary named scopes.
- Keeping them separate avoids a complex unified policy schema that would mix incompatible concepts.

---

## Why Context-Propagated Logging?

**Decision**: `notation-go/log` defines a `Logger` interface thread via `context.Context` rather than using a global logger.

**Reasoning**:
- The library layer (`notation-go`) must not force a specific logging framework on consumers; it must work with logrus, zap, slog, or any other logger.
- Context propagation ensures per-request loggers (with request-specific fields) flow through the entire call chain without parameter pollution.
- The CLI sets up logrus in `main.go`; library code calls `log.GetLogger(ctx)` — the two are decoupled.

---

## Why tspclient-go for Timestamping?

**Decision**: RFC 3161 timestamping is handled by a dedicated `tspclient-go` library.

**Reasoning**:
- RFC 3161 Timestamp Authority protocol is complex: it requires constructing a `TimeStampReq` (ASN.1/DER), sending it to the TSA HTTP endpoint, and validating the `TimeStampResp` countersignature.
- Extracting this into a dedicated library (`github.com/notaryproject/tspclient-go`) maintains the principle that `notation-core-go` should handle envelopes and that the timestamping concern is orthogonal.
- The `Timestamper` interface in `notation-go/notation.go` allows callers to provide a custom TSA implementation or use the default HTTP-based one.

---

## Why Experimental Feature Flags?

**Decision**: `cmd/notation/internal/experimental/experimental.go` gates certain features behind `NOTATION_EXPERIMENTAL=1`.

**Reasoning**:
- Features like OCI layout signing (`--oci-layout`) and custom trust policy scope for OCI layout are not yet fully specified in the Notary Project specification.
- Experimental gating allows users to try upcoming features while making clear they may change before stabilisation.
- The flag is checked at command setup time (not in the library), keeping the library clean.
