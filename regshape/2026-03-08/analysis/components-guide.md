# regshape — Component Guide

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

This guide provides a detailed reference for each component in the regshape codebase, including its purpose, public API, key behaviors, and usage patterns.

---

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [Transport Layer](#transport-layer)
3. [Auth Layer](#auth-layer)
4. [Operations Layer](#operations-layer)
5. [Models Layer](#models-layer)
6. [Decorators Layer](#decorators-layer)
7. [Utilities](#utilities)
8. [Error Hierarchy](#error-hierarchy)

---

## CLI Commands

### `regshape` (main group) — `cli/main.py`

The root Click command group. All subcommands are registered here.

**Global options** (passed via Click context to all subcommands):
| Option | Type | Default | Description |
|---|---|---|---|
| `--insecure` | bool flag | False | Use HTTP instead of HTTPS |
| `--verbose` | bool flag | False | Enable curl-style HTTP debug output |
| `--break` | bool flag | False | Re-raise exceptions (no clean error handling) |
| `--break-rules` | bool flag | False | Skip verification/validation steps |
| `--log-file` | path | None | Write output to a log file |

---

### `regshape auth` — `cli/auth.py`

**Commands:**

#### `login [OPTIONS] REGISTRY`
Authenticates to a registry and stores credentials.

| Option | Description |
|---|---|
| `--username TEXT` | Registry username |
| `--password TEXT` | Registry password (discouraged; use `--password-stdin`) |
| `--password-stdin` | Read password from stdin |

Flow:
1. Resolve credentials (explicit → Docker config → anon)
2. Attempt a test request to verify credentials work
3. Store validated credentials via `store_credentials()`

#### `logout REGISTRY`
Removes stored credentials for a registry.
- Calls `erase_credentials(registry)`

---

### `regshape blob` — `cli/blob.py`

**Commands:**

| Command | Description | Key Options |
|---|---|---|
| `head REGISTRY/REPO@DIGEST` | Check if blob exists | `--output json` |
| `get REGISTRY/REPO@DIGEST` | Download blob | `--output FILE`, `--stdout` |
| `push REGISTRY/REPO FILE` | Upload blob | `--media-type`, `--chunked` |
| `delete REGISTRY/REPO@DIGEST` | Delete blob | `--force` |
| `mount REGISTRY/REPO@DIGEST TARGET_REPO` | Cross-repo mount | — |

---

### `regshape manifest` — `cli/manifest.py`

| Command | Description |
|---|---|
| `get REGISTRY/REPO:TAG` | Download and print manifest JSON |
| `head REGISTRY/REPO:TAG` | Get manifest metadata (digest, size, media type) |
| `push REGISTRY/REPO:TAG FILE` | Push manifest from a JSON file |
| `delete REGISTRY/REPO:TAG` | Delete manifest by tag or digest |

---

### `regshape tag` — `cli/tag.py`

| Command | Description | Key Options |
|---|---|---|
| `list REGISTRY/REPO` | List all tags | `--n NUM`, `--last TAG` |
| `delete REGISTRY/REPO:TAG` | Delete a tag | `--force` |

---

### `regshape catalog` — `cli/catalog.py`

| Command | Description | Key Options |
|---|---|---|
| `list REGISTRY` | List all repositories | `--n NUM`, `--last REPO`, `--all` |

Note: Raises `CatalogNotSupportedError` if registry returns 404/405 (many private registries disable the catalog endpoint).

---

### `regshape referrer` — `cli/referrer.py`

| Command | Description | Key Options |
|---|---|---|
| `list REGISTRY/REPO@DIGEST` | List referrers (SBOM, signatures, etc.) | `--artifact-type`, `--output` |

---

### `regshape layout` — `cli/layout.py`

Operations on OCI Image Layout directories (local filesystem).

| Command | Description |
|---|---|
| `init PATH` | Initialize a new OCI Image Layout |
| `push REGISTRY/REPO:TAG LAYOUT_DIR` | Push image from registry into layout |
| `pull LAYOUT_DIR REGISTRY/REPO:TAG` | Push image from layout into registry |
| `list LAYOUT_DIR` | List images in a layout |
| `inspect LAYOUT_DIR DIGEST` | Inspect a manifest in a layout |

---

## Transport Layer

### `RegistryClient` — `libs/transport/client.py`

The **single HTTP gateway** for all registry communication.

**Constructor:**
```python
RegistryClient(config: TransportConfig)
```

**`TransportConfig` fields:**
| Field | Type | Description |
|---|---|---|
| `registry` | str | Registry hostname (e.g., `registry.io`) |
| `username` | Optional[str] | Resolved username |
| `password` | Optional[str] | Resolved password |
| `insecure` | bool | Use HTTP (default: False) |
| `verbose` | bool | Enable debug logging |
| `enable_retry` | bool | Enable retry middleware |
| `enable_caching` | bool | Enable caching middleware |

**Methods:**
```python
def get(self, path: str, headers: dict = None, **kwargs) -> RegistryResponse
def head(self, path: str, headers: dict = None, **kwargs) -> RegistryResponse
def put(self, path: str, headers: dict = None, body=None, **kwargs) -> RegistryResponse
def delete(self, path: str, headers: dict = None, **kwargs) -> RegistryResponse
def post(self, path: str, headers: dict = None, body=None, **kwargs) -> RegistryResponse
def patch(self, path: str, headers: dict = None, body=None, **kwargs) -> RegistryResponse

@property
def base_url(self) -> str  # https://registry or http://registry if insecure
```

**Behavior:**
- All methods construct `RegistryRequest` and pass to `MiddlewarePipeline`
- `MiddlewarePipeline` always includes `AuthMiddleware`
- Optionally includes `LoggingMiddleware`, `RetryMiddleware`, `CachingMiddleware`

---

### `MiddlewarePipeline` — `libs/transport/middleware.py`

**Middleware types:**

| Class | Purpose | When Active |
|---|---|---|
| `AuthMiddleware` | 401→token→retry | Always |
| `LoggingMiddleware` | curl-style request/response debug | `verbose=True` |
| `RetryMiddleware` | Configurable retry on failures | `enable_retry=True` |
| `CachingMiddleware` | Response caching | `enable_caching=True` |

**`RetryConfig` fields:**
```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    retry_on_status: frozenset = frozenset({429, 500, 502, 503, 504})
    backoff_factor: float = 1.0
    retry_on_exceptions: tuple = (ConnectionError, Timeout)
```

---

### `RegistryRequest` / `RegistryResponse` — `libs/transport/models.py`

```python
@dataclass
class RegistryRequest:
    method: str           # "GET", "HEAD", "PUT", etc.
    url: str              # Full URL
    headers: dict
    body: Optional[Union[bytes, Iterable[bytes]]]  # Streaming support
    params: Optional[dict]

@dataclass
class RegistryResponse:
    status_code: int
    headers: dict
    body: bytes
    elapsed: float        # Request duration in seconds

    @classmethod
    def from_requests_response(cls, r: requests.Response) -> "RegistryResponse"
```

---

## Auth Layer

### `resolve_credentials()` — `libs/auth/credentials.py`

```python
def resolve_credentials(
    registry: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    docker_config: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]
```

**Priority chain:**
1. Explicit `username`/`password` arguments
2. `credHelpers` map in Docker config → exec `docker-credential-{store} get`
3. `auths` map in Docker config → Base64 decode `user:pass`
4. Returns `(None, None)` for anonymous access

---

### `store_credentials()` and `erase_credentials()` — `libs/auth/credentials.py`

```python
def store_credentials(registry: str, username: str, password: str, docker_config: Optional[str] = None) -> None
def erase_credentials(registry: str, docker_config: Optional[str] = None) -> None
```

Uses credential helpers first if configured, otherwise writes to Docker config file.

---

### `authenticate()` — `libs/auth/registryauth.py`

```python
def authenticate(
    username: Optional[str],
    password: Optional[str],
    challenge: str  # WWW-Authenticate header value
) -> Optional[str]  # Returns "Bearer {token}" or "Basic {b64}" header value
```

Handles both Bearer token and Basic auth flows.

---

## Operations Layer

All operation functions follow a consistent signature pattern:
```python
def operation_name(client: RegistryClient, registry: str, repo: str, reference: str, ...) -> ReturnType
```

### Blob Operations — `libs/blobs/operations.py`

```python
def head_blob(client, registry, repo, digest) -> Optional[BlobInfo]
def get_blob(client, registry, repo, digest, output_path=None) -> bytes
def push_blob_monolithic(client, registry, repo, data: bytes, media_type: str) -> Descriptor
def push_blob_chunked(client, registry, repo, data_iter: Iterable[bytes], media_type: str, chunk_size=None) -> Descriptor
def delete_blob(client, registry, repo, digest) -> None
def mount_blob(client, registry, source_repo, target_repo, digest) -> bool
```

**Key behavior:**
- `get_blob()` streams response and verifies SHA-256/SHA-512 digest after download
- `push_blob_monolithic()` skips upload if blob already exists (HEAD check first)
- `push_blob_chunked()` sends data in segments using PATCH requests + final PUT

---

### Manifest Operations — `libs/manifests/operations.py`

```python
def get_manifest(client, registry, repo, reference) -> ImageManifest | ImageIndex
def head_manifest(client, registry, repo, reference) -> dict  # digest, size, media_type
def push_manifest(client, registry, repo, reference, manifest: dict | str, media_type: str) -> str  # digest
def delete_manifest(client, registry, repo, reference) -> None
```

---

### Tag Operations — `libs/tags/operations.py`

```python
def list_tags(client, registry, repo, n=None, last=None) -> TagList
def delete_tag(client, registry, repo, tag) -> None
```

`list_tags()` supports pagination via `n` (page size) and `last` (cursor). Follows OCI pagination spec.

`delete_tag()` works by fetching the tag's manifest digest, then deleting the manifest by digest (OCI spec doesn't have a direct tag delete endpoint).

---

### Catalog Operations — `libs/catalog/operations.py`

```python
def list_catalog(client, registry, n=None, last=None) -> RepositoryCatalog
def list_catalog_all(client, registry) -> list[str]  # Follows Link headers
```

`list_catalog_all()` follows `Link: <url>; rel="next"` headers to paginate through all repos automatically.

Raises `CatalogNotSupportedError` if the registry returns HTTP 404 or 405.

---

### Referrer Operations — `libs/referrers/operations.py`

```python
def list_referrers(client, registry, repo, digest, artifact_type=None) -> ReferrerList
def list_referrers_all(client, registry, repo, digest, artifact_type=None) -> list[Descriptor]
```

Implements OCI Referrers API (GET `/v2/{repo}/referrers/{digest}`). If the registry doesn't support the Referrers API, falls back to tag-based referrer discovery.

Optional `artifact_type` filtering: applied server-side if supported, otherwise client-side.

---

### Layout Operations — `libs/layout/operations.py`

```python
def init_layout(path: str) -> None
def read_index(path: str) -> ImageIndex
def write_index(path: str, index: ImageIndex) -> None
def read_manifest(path: str, digest: str) -> ImageManifest
def write_manifest(path: str, manifest: dict, media_type: str) -> str  # digest
def read_blob(path: str, digest: str) -> bytes
def write_blob(path: str, data: bytes) -> str  # digest
def get_blob_path(path: str, digest: str) -> pathlib.Path
def _write_atomically(target_path: str, data: bytes) -> None
```

All writes use `_write_atomically()` which uses `tempfile.mkstemp()` + `os.replace()`.

---

## Models Layer

### `parse_manifest()` — `libs/models/manifest.py`

Factory function that dispatches on `Content-Type`/`mediaType`:
```python
def parse_manifest(body: bytes | str, media_type: str = None) -> ImageManifest | ImageIndex
```

- Returns `ImageIndex` for `OCI_IMAGE_INDEX` or `DOCKER_MANIFEST_LIST_V2`
- Returns `ImageManifest` for everything else

### `Descriptor` — `libs/models/descriptor.py`

Core OCI primitive used everywhere:
```python
@dataclass
class Descriptor:
    mediaType: str
    digest: str       # Must match r"^sha(256:[a-f0-9]{64}|512:[a-f0-9]{128})$"
    size: int
    urls: Optional[list[str]] = None
    annotations: Optional[dict[str, str]] = None
    platform: Optional[Platform] = None
    artifactType: Optional[str] = None
```

### Media Type Constants — `libs/models/mediatype.py`

Key frozensets for membership testing:
```python
MANIFEST_MEDIA_TYPES  # OCI + Docker single-arch manifest types
INDEX_MEDIA_TYPES     # OCI + Docker multi-arch index types
ALL_MANIFEST_MEDIA_TYPES  # Union of both sets
```

---

## Decorators Layer

### `@track_time` — `libs/decorators/timing.py`

```python
@track_time
def my_operation(client, ...):
    ...
```

Accumulates `(function_qualname, elapsed_seconds)` tuples into `TelemetryConfig.method_timings`. Used by `@track_scenario` to render timing blocks.

### `@track_scenario(name)` — `libs/decorators/scenario.py`

```python
@track_scenario("push blob")
def push_blob_monolithic(client, ...):
    ...
```

Wraps a multi-step operation. After the decorated function returns, renders a `── telemetry ──` block showing timing for all inner `@track_time` calls, then clears `method_timings`.

### `redact_headers()` — `libs/decorators/sanitization.py`

```python
SENSITIVE_HEADERS = frozenset({
    "authorization",
    "proxy-authorization", 
    "cookie",
    "set-cookie"
})

def redact_headers(headers: dict) -> dict:
    """Return copy of headers with sensitive values redacted."""
    # Authorization: Bearer tokenvalue → Authorization: Bearer [REDACTED]
    # Cookie: session=abc → Cookie: [REDACTED]
```

Preserves auth scheme keyword (Basic/Bearer) while redacting the credential value.

---

## Utilities

### `parse_image_ref()` — `libs/refs.py`

```python
def parse_image_ref(ref: str) -> tuple[str, str, str]:
    """Parse image reference into (registry, repo, reference).
    
    Examples:
      "registry.io/myrepo:tag"         → ("registry.io", "myrepo", "tag")
      "registry.io/myrepo@sha256:abc"  → ("registry.io", "myrepo", "sha256:abc")
      "localhost:5000/myrepo"          → ("localhost:5000", "myrepo", "latest")
    """
```

Handles:
- Tag references (`:tag`)
- Digest references (`@sha256:...`)
- Default to `latest` when no tag/digest
- localhost with port
- Registry with port number

---

## Error Hierarchy

```python
class RegShapeError(Exception): pass

class AuthError(RegShapeError): pass
class ManifestError(RegShapeError): pass
class TagError(RegShapeError): pass
class BlobError(RegShapeError): pass
class CatalogError(RegShapeError): pass
class CatalogNotSupportedError(CatalogError): pass  # 404/405 from registry
class ReferrerError(RegShapeError): pass
class LayoutError(RegShapeError): pass
```

All errors include a descriptive message. The `--break` CLI option causes these to propagate as exceptions (for debugging) instead of being caught and displayed as user-friendly errors.
