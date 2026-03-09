# regshape — Mermaid Architecture Diagrams

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph User["User Interface"]
        CLI["regshape CLI<br/>(Click)"]
    end

    subgraph LibLayer["Library Layer (libs/)"]
        subgraph Transport["Transport"]
            RC["RegistryClient"]
            MW["MiddlewarePipeline<br/>Auth / Log / Retry / Cache"]
        end

        subgraph Auth["Auth"]
            CRED["credentials.py<br/>Credential Resolution"]
            DCFG["dockerconfig.py<br/>Docker config.json"]
            DCS["dockercredstore.py<br/>Credential Helpers"]
            RA["registryauth.py<br/>Bearer / Basic Auth"]
        end

        subgraph Ops["Operations"]
            BLOBS["blobs/operations.py"]
            MFSTS["manifests/operations.py"]
            TAGS["tags/operations.py"]
            CAT["catalog/operations.py"]
            REF["referrers/operations.py"]
            LAY["layout/operations.py"]
        end

        subgraph Models["Models"]
            MAN["ImageManifest / ImageIndex"]
            DESC["Descriptor / Platform"]
            BLOB_M["BlobInfo / BlobUploadSession"]
            ERR["OciErrorResponse"]
            MT["mediatype constants"]
        end

        subgraph Dec["Decorators"]
            TIMING["@track_time"]
            SCEN["@track_scenario"]
            METR["PerformanceMetrics"]
            SANIT["redact_headers()"]
        end
    end

    subgraph Registry["OCI Registry"]
        REG["Container Registry<br/>(Docker Hub / GHCR / ACR / etc.)"]
    end

    subgraph FS["Filesystem"]
        OCI_LAYOUT["OCI Image Layout"]
    end

    CLI --> RC
    CLI --> Ops
    Ops --> RC
    RC --> MW
    RC --> CRED
    CRED --> DCFG
    CRED --> DCS
    MW --> RA
    MW --> REG
    LAY --> OCI_LAYOUT
```

---

## 2. CLI Command Hierarchy

```mermaid
graph LR
    MAIN["regshape<br/>--insecure --verbose<br/>--break --log-file"]

    MAIN --> AUTH["auth"]
    MAIN --> BLOB["blob"]
    MAIN --> CAT["catalog"]
    MAIN --> LAY2["layout"]
    MAIN --> MFST["manifest"]
    MAIN --> RFRR["referrer"]
    MAIN --> TAG["tag"]

    AUTH --> LOGIN["login"]
    AUTH --> LOGOUT["logout"]

    BLOB --> B_HEAD["head"]
    BLOB --> B_GET["get"]
    BLOB --> B_PUSH["push"]
    BLOB --> B_DEL["delete"]
    BLOB --> B_MNT["mount"]

    CAT --> C_LIST["list"]

    LAY2 --> L_INIT["init"]
    LAY2 --> L_PUSH["push"]
    LAY2 --> L_PULL["pull"]
    LAY2 --> L_LIST["list"]
    LAY2 --> L_INS["inspect"]

    MFST --> M_GET["get"]
    MFST --> M_HEAD["head"]
    MFST --> M_PUSH["push"]
    MFST --> M_DEL["delete"]

    RFRR --> R_LIST["list"]

    TAG --> T_LIST["list"]
    TAG --> T_DEL["delete"]
```

---

## 3. Middleware Pipeline

```mermaid
sequenceDiagram
    participant OPS as Operations
    participant RC as RegistryClient
    participant AUTH_MW as AuthMiddleware
    participant LOG_MW as LoggingMiddleware  
    participant RETRY_MW as RetryMiddleware
    participant HTTP as HTTP (requests)
    participant REG as Registry

    OPS->>RC: get/put/post/delete(path, headers, body)
    RC->>AUTH_MW: execute(request)
    AUTH_MW->>LOG_MW: next(request)
    LOG_MW->>RETRY_MW: next(request)
    RETRY_MW->>HTTP: requests.{method}(url, ...)
    HTTP->>REG: HTTP request
    REG-->>HTTP: 401 Unauthorized (WWW-Authenticate: Bearer ...)
    HTTP-->>RETRY_MW: response
    RETRY_MW-->>LOG_MW: response
    LOG_MW-->>AUTH_MW: response (401)
    AUTH_MW->>AUTH_MW: parse WWW-Authenticate
    AUTH_MW->>REG: POST /token endpoint (Bearer) or skip (Basic)
    REG-->>AUTH_MW: {"access_token": "..."}
    AUTH_MW->>LOG_MW: retry request + Authorization: Bearer {token}
    LOG_MW->>RETRY_MW: next(request)
    RETRY_MW->>HTTP: requests.{method}(...)
    HTTP->>REG: HTTP request + Auth
    REG-->>HTTP: 200 OK
    HTTP-->>RETRY_MW: 200
    RETRY_MW-->>LOG_MW: 200
    LOG_MW-->>AUTH_MW: 200
    AUTH_MW-->>RC: RegistryResponse
    RC-->>OPS: RegistryResponse
```

---

## 4. Authentication Flow

```mermaid
flowchart TD
    START([Request needs auth]) --> CHECK_401{Response is 401?}
    CHECK_401 -- No --> SUCCESS([Return response])
    CHECK_401 -- Yes --> PARSE_WWW[Parse WWW-Authenticate header]
    
    PARSE_WWW --> BEARER{Bearer scheme?}
    BEARER -- Yes --> RESOLVE_CREDS[Resolve credentials]
    BEARER -- No --> BASIC[Build Basic auth header<br/>Base64 user:pass]
    
    RESOLVE_CREDS --> CRED_CHAIN{Credential priority chain}
    CRED_CHAIN --> EXPLICIT[1. Explicit --username/--password]
    CRED_CHAIN --> CRED_HELPER[2. credHelpers in docker config]
    CRED_CHAIN --> DOCKER_AUTHS[3. auths in docker config]
    CRED_CHAIN --> ANON[4. Anonymous]
    
    EXPLICIT --> TOKEN_EP[POST token endpoint<br/>with credentials]
    CRED_HELPER --> HELPER_PROC[Exec docker-credential-{store}<br/>subprocess]
    HELPER_PROC --> TOKEN_EP
    DOCKER_AUTHS --> DECODE[Decode Base64 user:pass] 
    DECODE --> TOKEN_EP
    ANON --> TOKEN_EP
    
    TOKEN_EP --> GOT_TOKEN{Token received?}
    GOT_TOKEN -- Yes --> RETRY[Retry with Authorization: Bearer {token}]
    GOT_TOKEN -- No --> BASIC
    
    BASIC --> RETRY
    RETRY --> SUCCESS
```

---

## 5. Blob Push Flow

```mermaid
flowchart TD
    START([push_blob called]) --> HEAD[HEAD /v2/repo/blobs/digest<br/>Check if blob exists]
    HEAD --> EXISTS{200 OK?}
    EXISTS -- Yes --> SKIP([Skip — blob already exists<br/>Return existing Descriptor])
    EXISTS -- No --> MONO{Monolithic or Chunked?}
    
    MONO -- Monolithic --> POST[POST /v2/repo/blobs/uploads/<br/>Initiate upload → 202]
    POST --> EXTRACT[Extract Location header<br/>= upload URL]
    EXTRACT --> PUT[PUT {upload_url}?digest={digest}<br/>with full blob body]
    PUT --> CHECK{201 Created?}
    CHECK -- Yes --> RETURN([Return Descriptor<br/>mediaType, digest, size])
    CHECK -- No --> ERR([Raise BlobError])

    MONO -- Chunked --> POST2[POST /v2/repo/blobs/uploads/<br/>Initiate → 202]
    POST2 --> CHUNKS[For each chunk:<br/>PATCH {upload_url} with bytes<br/>Update Range header]
    CHUNKS --> FINAL_PUT[PUT {upload_url}?digest={digest}<br/>Finalize upload]
    FINAL_PUT --> RETURN
```

---

## 6. OCI Image Layout Write (Atomic)

```mermaid
flowchart LR
    DATA[Data to write] --> MKSTEMP[tempfile.mkstemp<br/>parent_dir, .tmp suffix]
    MKSTEMP --> WRITE[Write to temp file]
    WRITE --> REPLACE[os.replace temp → target]
    REPLACE --> ATOMIC([Atomic on POSIX<br/>No partial state])
    
    subgraph Filesystem State
        TMP["file.json.tmp<br/>(intermediate)"]
        FINAL["file.json<br/>(final)"]
    end
    
    MKSTEMP --> TMP
    WRITE --> TMP
    REPLACE --> FINAL
```

---

## 7. Module Dependency Graph

```mermaid
graph TB
    subgraph CLI
        main_cli["cli/main.py"]
        auth_cli["cli/auth.py"]
        blob_cli["cli/blob.py"]
        cat_cli["cli/catalog.py"]
        layout_cli["cli/layout.py"]
        manifest_cli["cli/manifest.py"]
        referrer_cli["cli/referrer.py"]
        tag_cli["cli/tag.py"]
    end

    subgraph CoreLibs["Core Libraries"]
        transport_client["libs/transport/client.py"]
        transport_mw["libs/transport/middleware.py"]
        auth_creds["libs/auth/credentials.py"]
        auth_reg["libs/auth/registryauth.py"]
        refs["libs/refs.py"]
        errors["libs/errors.py"]
    end

    subgraph OpsLibs["Operations"]
        ops_blobs["libs/blobs/operations.py"]
        ops_manifests["libs/manifests/operations.py"]
        ops_tags["libs/tags/operations.py"]
        ops_catalog["libs/catalog/operations.py"]
        ops_referrers["libs/referrers/operations.py"]
        ops_layout["libs/layout/operations.py"]
    end

    subgraph ModelLibs["Models"]
        models_manifest["libs/models/manifest.py"]
        models_descriptor["libs/models/descriptor.py"]
        models_mediatype["libs/models/mediatype.py"]
        models_error["libs/models/error.py"]
    end

    subgraph DecLibs["Decorators"]
        dec_timing["libs/decorators/timing.py"]
        dec_scenario["libs/decorators/scenario.py"]
        dec_sanitization["libs/decorators/sanitization.py"]
    end

    auth_cli --> auth_creds
    blob_cli --> ops_blobs
    cat_cli --> ops_catalog
    layout_cli --> ops_layout
    manifest_cli --> ops_manifests
    referrer_cli --> ops_referrers
    tag_cli --> ops_tags

    auth_cli --> transport_client
    blob_cli --> transport_client
    manifest_cli --> transport_client

    transport_client --> transport_mw
    transport_client --> auth_creds
    transport_mw --> auth_reg
    transport_mw --> dec_sanitization

    auth_creds --> auth_reg

    ops_blobs --> models_descriptor
    ops_manifests --> models_manifest
    ops_manifests --> models_mediatype
    ops_tags --> models_error
    ops_catalog --> models_error
    ops_referrers --> models_manifest

    ops_blobs --> dec_timing
    ops_blobs --> dec_scenario
    ops_manifests --> dec_timing
    ops_tags --> dec_timing
    ops_catalog --> dec_timing
    ops_referrers --> dec_timing
    ops_layout --> dec_timing

    models_manifest --> models_mediatype
    models_manifest --> models_descriptor
```

---

## 8. Telemetry and Observability Model

```mermaid
graph LR
    OPS["Operation<br/>@track_time"] --> TC["TelemetryConfig<br/>method_timings list"]
    OPS2["Scenario<br/>@track_scenario"] --> BLOCK["Telemetry Block<br/>rendered to stdout/log"]
    
    BLOCK --> TEXT["── telemetry ──<br/>plain text format"]
    BLOCK --> NDJSON["NDJSON stream<br/>one JSON per line"]
    
    RC["RegistryClient<br/>middleware"] --> METRICS["PerformanceMetrics<br/>requests / bytes / retries / errors"]
    
    subgraph RedactionLayer["Security Layer"]
        SANIT["redact_headers()<br/>Authorization → Bearer [REDACTED]<br/>Cookie → [REDACTED]"]
    end
    
    OPS --> SANIT
    SANIT --> LOG["LoggingMiddleware<br/>curl-style debug output"]
```

---

## 9. Error Hierarchy

```mermaid
classDiagram
    class RegShapeError {
        <<base>>
    }
    class AuthError
    class ManifestError
    class TagError
    class BlobError
    class CatalogError
    class CatalogNotSupportedError
    class ReferrerError
    class LayoutError

    RegShapeError <|-- AuthError
    RegShapeError <|-- ManifestError
    RegShapeError <|-- TagError
    RegShapeError <|-- BlobError
    RegShapeError <|-- CatalogError
    CatalogError <|-- CatalogNotSupportedError
    RegShapeError <|-- ReferrerError
    RegShapeError <|-- LayoutError
```

---

## 10. Data Model

```mermaid
classDiagram
    class ImageManifest {
        +schemaVersion: int
        +mediaType: str
        +config: Descriptor
        +layers: list[Descriptor]
        +subject: Optional[Descriptor]
        +artifactType: Optional[str]
        +annotations: Optional[dict]
    }

    class ImageIndex {
        +schemaVersion: int
        +mediaType: str
        +manifests: list[Descriptor]
        +subject: Optional[Descriptor]
        +artifactType: Optional[str]
        +annotations: Optional[dict]
    }

    class Descriptor {
        +mediaType: str
        +digest: str
        +size: int
        +urls: Optional[list]
        +annotations: Optional[dict]
        +platform: Optional[Platform]
        +artifactType: Optional[str]
    }

    class Platform {
        +architecture: str
        +os: str
        +variant: Optional[str]
    }

    class BlobInfo {
        +digest: str
        +size: int
        +mediaType: Optional[str]
    }

    class BlobUploadSession {
        +location: str
        +range: Optional[str]
    }

    class OciErrorResponse {
        +errors: list[dict]
        +first_detail(): str
    }

    ImageManifest --> Descriptor : config + layers
    ImageIndex --> Descriptor : manifests
    Descriptor --> Platform : optional
```
