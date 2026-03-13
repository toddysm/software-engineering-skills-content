# Attack Surface Map — Notation Project

**Generated**: 2026-03-12
**Architecture Type**: Single-user CLI client (no server component)

---

## Overview

Notation is a CLI binary (`notation`) — it has **no persistent network listener**, **no daemon process**, and **no server component**. The attack surface is therefore limited to:

1. Inputs the user provides at the command line
2. Files the tool reads from and writes to
3. Network connections the tool initiates (outbound only)
4. Plugin subprocess execution
5. Data returned by external systems (OCI registry, TSA)

This is a fundamentally different (and smaller) attack surface than a server-side application.

---

## Attack Surface Map

```
┌─────────────────────────────────────────────────────────────────┐
│                      ATTACKER CONTROL                           │
│                                                                  │
│  [Malicious File]   [Malicious Registry]   [Malicious Plugin]   │
│       │                    │                       │            │
└───────┼────────────────────┼───────────────────────┼────────────┘
        │                    │                       │
        ▼                    ▼                       ▼
┌───────────────────────────────────────────────────────────────┐
│                    notation CLI Binary                         │
│                                                                │
│  stdin/stdout/stderr    command-line args    env vars         │
│  (USER-CONTROLLED)      (USER-CONTROLLED)   (USER-CONTROLLED) │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  File I/O    │  │ OCI Registry │  │  Plugin Subprocess   │ │
│  │  (Surface 1) │  │  (Surface 2) │  │    (Surface 3)       │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  Trust Policy│  │ Timestamp    │  │  Credential Helper   │ │
│  │  (Surface 4) │  │ Authority    │  │    (Surface 5)       │ │
│  └──────────────┘  │  (Surface 6) │  └──────────────────────┘ │
│                    └──────────────┘                            │
└───────────────────────────────────────────────────────────────┘
```

---

## Surface 1: Local File System Access

### Description
Notation reads from and writes to the local file system for:
- Trust policy JSON (`~/.config/notation/trustpolicy.oci.json`)
- Certificate trust stores (`~/.config/notation/truststore/`)
- Plugin binaries (`~/.config/notation/plugins/`)
- Key configuration (`~/.config/notation/signingkeys.json`)
- Artifact files (blob sign/verify mode — user-provided path)

### Trust Boundary
All local files are in the user's own directory tree (under `$XDG_CONFIG_HOME/notation` or `~/.config/notation`). An attacker who can freely modify these files has already achieved local code execution as the same user — Notation provides no additional privilege escalation.

### Risk Assessment

| Sub-surface | Attacker Need | Current Control | Residual Risk |
|-------------|--------------|----------------|--------------|
| Trust policy tampering | Write access to `~/.config/notation/` | Trust policy schema validation; JSON parse errors abort verification | LOW — requires local access |
| Certificate store tampering | Write access to `~/.config/notation/truststore/` | X.509 validation rejects malformed certs | LOW — requires local access |
| Artifact file (blob mode) | Attacker provides path that resolves to sensitive file | None — user chooses what to sign; intentional | INTENDED — user-controlled |
| Config file path traversal | Attacker controls a path variable reaching `osutil.Copy/WriteFile` | Partial — paths come from `dir` package | LOW — G304 finding; add `filepath.Clean()` |

### Attack Scenario: Configuration File Symlink Attack

A local attacker who cannot write notation config directly could plant a symlink in the notation config directory pointing to a victim file. If notation were then run with elevated privileges (which it isn't by design), the symlink could redirect a write to an unintended location.

**Mitigation**: Notation should never be run as root. The plugin installer (`plugin install`) adds an `os.Lstat` check before opening to detect symlinks to some extent.

---

## Surface 2: OCI Registry Communication

### Description
Notation connects to OCI registries to:
- Resolve image/artifact references (`Sign`, `Verify`)
- List existing signature manifests (Referrers API)
- Fetch signature blob content
- Push new signature manifests

### Trust Boundary
The registry is an **external network service**. It is either:
- A trusted internal registry (user's own infrastructure)
- A public registry (Docker Hub, GHCR, ACR, etc.)

**Key insight**: Notation's verification works EVEN AGAINST A MALICIOUS REGISTRY because the signature itself is validated cryptographically against the signer's certificate, which is validated against the trust policy. A registry that returns a forged signature blob will fail signature verification.

### Risk Assessment

| Sub-surface | Attacker Need | Current Control | Residual Risk |
|-------------|--------------|----------------|--------------|
| Forged signature blob | Control of registry | Cryptographic signature verification; cert chain validation | VERY LOW — must forge or compromise signer key |
| Malformed JSON envelope | Control of registry response | `encoding/json` parser; envelope schema validation | LOW — parser-level robustness |
| Malformed CBOR (COSE) | Control of registry response | `fxamacker/cbor/v2` with fuzz coverage | LOW |
| OCI reference injection | User provides malformed reference | `oras-go` reference parser validates before network call | LOW |
| Man-in-the-Middle | Network position between user and registry | TLS required by default; `--insecure-registry` must be explicit | LOW with TLS |

### Attack Scenario: Replay Attack (Signature Substitution)

An attacker who controls the registry could return a valid signature for a different artifact (e.g., return signatures from image A when queried for image B).

**Mitigation**: The signature envelope contains the artifact digest (`subject.digest`). The verifier checks that the signature's subject digest matches the artifact digest being verified. Cross-artifact substitution is detected.

---

## Surface 3: Plugin Subprocess Execution

### Description
Notation invokes plugin binaries as subprocesses to:
- Generate signatures (key-based plugins: HSM, TPM, cloud KMS)
- Verify signature extensions
- Describe key metadata

### Trust Boundary
Plugins are binaries in `~/.config/notation/plugins/<name>/`. The user installs them; they run with the user's privileges.

### Risk Assessment

| Sub-surface | Attacker Need | Current Control | Residual Risk |
|-------------|--------------|----------------|--------------|
| Malicious plugin execution | Write access to plugins directory | Filesystem permissions; plugin name validation | MEDIUM — user must have installed malicious plugin |
| Plugin path traversal | Control of plugin name string | Plugin name validated to `notation-<alphanumeric>` pattern | LOW |
| Environment variable injection to plugin | Attacker controls notation env vars | Subprocess inherits only sanitised env | LOW |
| JSON response injection from plugin | Compromised plugin binary | Plugin response schema validated; malformed responses rejected | LOW IF plugin is compromised |

### Attack Scenario: Malicious Plugin Binary

The most direct attack: install a plugin binary that, when invoked by notation, performs malicious actions (data exfiltration, key theft from HSM, etc.).

**Mitigation**: 
1. Plugin installation can (and should) require plugin signature verification — notation can verify a plugin's own signature during `notation plugin add`.
2. The plugin subprocess is constrained by OS filesystem permissions.
3. Defence-in-depth: key material lives in the plugin's own process; a compromised plugin cannot directly access other plugins' keys.

---

## Surface 4: Trust Policy Document

### Description
The trust policy JSON is the central authorization document. It determines which signing identities are trusted for which registry/repository scopes.

### Trust Boundary
The trust policy file is owned by the local user (`~/.config/notation/trustpolicy.oci.json`). It is loaded once per `verify` command invocation.

### Risk Assessment

| Sub-surface | Attacker Need | Current Control | Residual Risk |
|-------------|--------------|----------------|--------------|
| Trust policy tampering | Write access to `~/.config/notation/` | Requires local access; schema validation catches structural errors | LOW |
| Trust scope confusion | Attacker crafts registry ref that matches a too-broad wildcard | Wildcard semantics are explicitly defined; `*` only at segment level | LOW |
| Policy bypass via malformed JSON | Attacker provides malformed trust policy | JSON parse errors abort verification entirely | VERY LOW |

### Attack Scenario: Scope Wildcard Exploitation

If a trust policy uses `*` as a wildcard for `registryScopes`, it matches all registries. A misconfigured policy could allow an attacker to publish a signed artifact to any registry and have it verified.

**Mitigation**: The schema validation in `trustpolicy` rejects standalone `*` except when combined with a specific identity principal. Users are warned in documentation against overly broad scopes.

---

## Surface 5: Credential Helper Interaction

### Description
Notation uses Docker credential helpers (`~/.docker/config.json`) for registry authentication. It calls `notation login` which in turn calls the configured credential helper binary.

### Trust Boundary
Credential helpers are external binaries installed by the user.

### Risk Assessment

| Sub-surface | Attacker Need | Current Control | Residual Risk |
|-------------|--------------|----------------|--------------|
| Malicious credential helper | Write access to credential helper binary or PATH manipulation | Credential helper path comes from Docker config | MEDIUM — standard credential helper attack surface |
| Password entered at terminal | Shoulder surfing, memory scraping | `term.ReadPassword` disables echo; credential not stored by notation | LOW |

---

## Surface 6: Timestamp Authority (RFC 3161)

### Description
When `--timestamp-url` is specified, notation makes an HTTPS POST to the TSA endpoint to obtain a countersignature.

### Trust Boundary
The TSA is an external network service. The TSA certificate must be in the notation trust store.

### Risk Assessment

| Sub-surface | Attacker Need | Current Control | Residual Risk |
|-------------|--------------|----------------|--------------|
| SSRF via timestamp URL | User provides malicious `--timestamp-url` | URL must resolve to HTTPS endpoint; network-level controls apply | LOW — user must pass flag |
| Tampered timestamp response | MITM or control of TSA | Timestamp countersig validated against TSA cert chain in trust store | LOW |
| TSA cert chain confusion | Compromise of TSA cert | TSA cert must be in user's trust store | LOW |

---

## No-Threat Areas (Explicitly Out of Scope)

The following attack classes **do not apply** to Notation:

| Attack Class | Reason Not Applicable |
|-------------|----------------------|
| SQL Injection | No database or SQL used anywhere |
| XSS / Content Injection | No web UI or HTML output |
| Authentication Bypass | No authentication server |
| Session Hijacking | No session concept |
| Privilege Escalation (service) | No background service or daemon |
| SSRF (server-side) | Not a server — all connections are client-initiated |
| CSRF | No web forms or HTTP endpoints |
| DoS via resource exhaustion (server) | No persistent process to exhaust |

---

## Threat Model Summary

```
THREAT ACTORS:
  [Remote Attacker]  ←  Cannot reach notation directly (no network listener)
                        Can control: registry content, TSA responses
  
  [Local Attacker]   ←  Can control: files in user home, plugins directory
                        (but already has user-level code execution)
  
  [Malicious Registry] ← Returns forged signatures
                         BLOCKED by cryptographic verification

  [Malicious Plugin]  ← Executes attacker code with user privileges  
                        MITIGATED by: user installs plugins, subprocess isolation

  [Compromised Dep]   ← CVE in transitive Go dependency
                        MITIGATED by: govulncheck 0 findings, periodic dep updates

VERDICT: LOW overall attack surface for a CLI security tool.
```
