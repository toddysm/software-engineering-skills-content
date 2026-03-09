# regshape — Technology Decisions

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

This document examines the key technology choices in regshape, explaining the rationale behind architectural decisions derived from code analysis.

---

## 1. Python as the Implementation Language

**Evidence:** `pyproject.toml` requires `python >= "3.10"`

**Why Python 3.10+:**
- Structural Pattern Matching (`match`/`case`) — available if needed for future OCI spec expansion
- Union types with `X | Y` syntax for cleaner type hints (used in models)
- `dataclasses` improvements
- Wide availability in DevOps/container tooling ecosystems

**Implication:** The code uses `dataclasses` extensively for models and configs, `typing` module for generics, and takes advantage of modern Python features like walrus operator and f-strings throughout.

---

## 2. Click for CLI Framework

**Evidence:** `cli/main.py`, all `cli/*.py` modules; `click>=8.1.0` in `pyproject.toml`

**Why Click over argparse/typer:**

| Aspect | Click | argparse | Notes |
|---|---|---|---|
| Decorator-based | ✅ | ❌ | Less boilerplate; natural command grouping |
| Context passing | ✅ Click Context | ❌ | Global options passed consistently to all subcommands |
| Subcommand groups | ✅ Built-in | ❌ Limited | `regshape.add_command(auth)` pattern |
| Type coercion | ✅ | ✅ | Click is more expressive |
| Testing | ✅ `CliRunner` | ✅ | Click test runner is superior |
| Maturity | ✅ Stable since 2014 | ✅ stdlib | Both stable |

**Specific Click features used:**
- `@click.group()` for `regshape` and each subgroup
- `@click.pass_context` to pass global options down
- `click.Context` object carries `insecure`, `verbose`, `break`, `log_file` flags
- `click.echo()` for output
- `@click.option()` and `@click.argument()` for parameters

---

## 3. requests Library for HTTP

**Evidence:** All `libs/transport/client.py` HTTP calls; `requests>=2.31.0` in `pyproject.toml`

**Why requests over httpx/urllib3/aiohttp:**

| Library | Sync | Async | Known API | Notes |
|---|---|---|---|---|
| `requests` | ✅ | ❌ | ✅ Ubiquitous | Used in regshape |
| `httpx` | ✅ | ✅ | Newer | More modern, similar API |
| `aiohttp` | ❌ | ✅ | Different | Would require async architecture |
| `urllib3` | Low-level | ❌ | Low-level | Used internally by requests |

**Decision rationale:**
- regshape is a synchronous CLI tool (no event loop needed)
- `requests` is universally known; lowers contributor barrier
- Well-maintained with robust TLS support via `urllib3` + `certifi`
- No performance benefit to async for a CLI tool that one user runs serially

**Note:** If regshape ever evolves into a library used in async applications, migrating to `httpx` would be a natural step (nearly identical API with async support).

---

## 4. Dataclasses for Models and Configuration

**Evidence:** `RegistryRequest`, `RegistryResponse`, `TransportConfig`, `BlobInfo`, `Descriptor`, `Platform`, `PerformanceMetrics`

**Why dataclasses:**
- Zero-dependency (stdlib)
- `@dataclass` generates `__init__`, `__repr__`, `__eq__` automatically
- Field defaults via `field(default_factory=...)` for mutable defaults
- Type annotations are self-documenting
- Lightweight vs Pydantic (no validation overhead for internal data transfer objects)

**Pattern:** All internal data transfer objects are dataclasses. External data (from registry JSON) is parsed manually into these dataclasses via `@classmethod` factory methods.

---

## 5. Middleware Pipeline Pattern

**Evidence:** `libs/transport/middleware.py` — `Middleware` Protocol, `MiddlewarePipeline`, `BaseMiddleware`, etc.

**Why middleware over direct requests in client:**

The `RegistryClient` could have directly implemented auth, retry, and logging in its `http_request()` method. Instead, a middleware pipeline was chosen.

**Benefits:**
- Each concern is isolated (auth ≠ retry ≠ logging)
- New behavior added without modifying existing code (Open/Closed principle)
- Each middleware is independently testable
- Pipeline composition is explicit and configurable at construction time
- `CachingMiddleware` stub shows the extensibility intent

**Implementation:**
```
AuthMiddleware → LoggingMiddleware → RetryMiddleware → actual HTTP call
```

Each middleware implements `process(request, next_middleware)` — standard chain-of-responsibility.

---

## 6. Decorator-Based Telemetry

**Evidence:** `@track_time` in all operations; `@track_scenario` in blob push/pull

**Why decorators:**
- Telemetry is a cross-cutting concern — decorators keep it out of business logic
- Operations code stays focused on correctness; telemetry accumulates invisibly
- Easy to disable (remove decorator) or adjust without touching operation code
- Consistent timing across all operations with zero per-operation boilerplate

**Pattern:**
```python
@track_time        # Outer: records (method_name, elapsed) per call
@track_scenario("push blob")  # Inner: renders summary block after completion
def push_blob_monolithic(...):
    # Pure business logic
    ...
```

---

## 7. Atomic File Writes for OCI Layout

**Evidence:** `libs/layout/operations.py` `_write_atomically()`

```python
def _write_atomically(target_path, data):
    fd, tmp_path = tempfile.mkstemp(dir=parent_dir, suffix=".tmp")
    try:
        os.write(fd, data)
        os.close(fd)
        os.replace(tmp_path, target_path)
    except:
        os.unlink(tmp_path)
        raise
```

**Why this matters:**
- `os.replace()` is atomic on POSIX systems — readers never see partial file state
- OCI Image Layout requires consistent `index.json`; partial writes would corrupt the layout
- The `tempfile.mkstemp()` + `os.replace()` pattern is the gold standard for safe file updates

---

## 8. Two-Layer Architecture (CLI + Library)

**Evidence:** `cli/` layer contains no business logic; `libs/` layer has no import of `cli/`

**Why separate CLI from library:**
- `regshape` can be imported and used as a Python library without Click
- Testing operations doesn't require invoking CLI
- Future SDK packaging: `libs/` can become a separate installable package
- Clean separation of concerns: I/O (CLI) vs logic (library)

**Evidence of clean separation:**
- All `cli/*.py` files: parse args, construct configs, call library functions, format output
- No `from regshape.cli import ...` anywhere in `libs/`
- Library functions are pure: take typed inputs, return typed outputs

---

## 9. SHA-256/SHA-512 Digest Verification

**Evidence:** `libs/blobs/operations.py` `get_blob()` and `libs/models/descriptor.py`

```python
# descriptor.py - strict validation
DIGEST_PATTERN = re.compile(r"^sha(256:[a-f0-9]{64}|512:[a-f0-9]{128})$")

# blobs/operations.py - verify after download
computed = hashlib.sha256(data).hexdigest()
if f"sha256:{computed}" != expected_digest:
    raise BlobError("Digest mismatch")
```

**Why both:**
- Strict regex in `Descriptor` catches malformed digest strings before any HTTP calls
- Post-download verification catches data corruption or MITM tampering
- OCI spec mandates digest verification; regshape correctly implements it

---

## 10. Bearer Token Authentication over Basic Auth Persistence

**Evidence:** `libs/auth/registryauth.py` — always attempts Bearer token; falls back to Basic only if needed

**Design principle:**
- Bearer tokens are short-lived (typically 1 hour): better security than long-lived Basic auth
- Per-request Bearer tokens: if a token is leaked, damage window is limited
- Basic auth is always sent over HTTPS, but still exposed in each request header
- OCI token spec is followed correctly: `access_token` field preferred over `token`

**Credential storage:**
- Credentials stored in Docker config (shared with Docker CLI) — no new credential format invented
- `credHelpers` supported: enables OS keychain (macOS Keychain, Windows Credential Manager, etc.)

---

## Summary: Technology Choices Matrix

| Decision | Choice Made | Alternative Considered | Key Reason |
|---|---|---|---|
| Language | Python 3.10+ | Go, Rust | Ecosystem fit; developer familiarity |
| CLI framework | Click | argparse, Typer | Context passing; subcommand groups |
| HTTP client | requests | httpx, urllib3 | Ubiquitous; sync is sufficient |
| Data models | dataclasses | Pydantic | Zero-dependency; no validation overhead for DTO |
| HTTP abstraction | Middleware pipeline | Direct in client | Separation of concerns; extensibility |
| Telemetry | Decorators | Explicit calls | Cross-cutting; keeps operations clean |
| File writes | mkstemp + os.replace | Direct write | Atomic on POSIX; OCI correctness |
| Auth | Bearer token first | Basic auth first | Shorter-lived; better security |
| Dependencies | Minimal (2 runtime) | Feature-rich ecosystem | Maximum portability |
