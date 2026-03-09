# regshape — Interactive Query Examples

**Project:** regshape v0.1.0  
**Analysis Date:** 2026-03-08  

This document provides examples of how to query the dependency analysis data files to answer common architectural questions.

---

## Querying the Dependency Database

The `dependency-query-db.json` file contains the full dependency graph. The `file-inventory.json` contains per-file function/class inventories.

---

## Query Examples

### Q1: What modules does `transport/client.py` depend on?

```bash
python3 -c "
import json
with open('source-files/file-inventory.json') as f:
    inv = json.load(f)

for file in inv.get('files', []):
    if 'transport/client' in file['path']:
        print('File:', file['path'])
        print('Imports:', file.get('imports', []))
        print('Functions:', [fn['name'] for fn in file.get('functions', [])])
        print('Classes:', [c['name'] for c in file.get('classes', [])])
"
```

### Q2: What modules import `libs/errors.py`? (reverse dependency lookup)

```bash
python3 -c "
import json
with open('dependencies/dependency-graph.json') as f:
    dep = json.load(f)

target = 'libs/errors.py'
reverse = dep.get('reverse_dependencies', {}).get(target, [])
print(f'{target} is imported by {len(reverse)} modules:')
for m in sorted(reverse):
    print(f'  {m}')
"
```

### Q3: Which files have the most internal dependencies?

```bash
python3 -c "
import json
with open('dependencies/dependency-graph.json') as f:
    dep = json.load(f)

forward = dep.get('forward_dependencies', {})
counts = sorted([(k, len(v)) for k, v in forward.items()], key=lambda x: -x[1])
print('Top 10 by outgoing dependencies:')
for path, count in counts[:10]:
    print(f'  {count:3d} imports: {path}')
"
```

### Q4: What is the blast radius if `libs/transport/client.py` changes?

```bash
python3 -c "
import json
from collections import deque

with open('dependencies/dependency-graph.json') as f:
    dep = json.load(f)

# BFS through reverse dependencies
target = 'libs/transport/client.py'
reverse = dep.get('reverse_dependencies', {})

visited = set()
queue = deque([target])
while queue:
    current = queue.popleft()
    for importer in reverse.get(current, []):
        if importer not in visited:
            visited.add(importer)
            queue.append(importer)

print(f'Modules affected if {target} changes:')
for m in sorted(visited):
    print(f'  {m}')
print(f'Total: {len(visited)} modules')
"
```

### Q5: List all classes and their methods

```bash
python3 -c "
import json
with open('source-files/file-inventory.json') as f:
    inv = json.load(f)

for file in inv.get('files', []):
    for cls in file.get('classes', []):
        print(f\"{file['path']} :: {cls['name']}\")
        for method in cls.get('methods', []):
            print(f\"  .{method['name']}()\")
" | grep -v '^tests/'
```

### Q6: What functions are decorated with `@track_time`?

```bash
python3 -c "
import json
with open('source-files/file-inventory.json') as f:
    inv = json.load(f)

for file in inv.get('files', []):
    for fn in file.get('functions', []):
        if 'track_time' in str(fn.get('decorators', [])):
            print(f\"{file['path']} :: {fn['name']}\")
"
```

### Q7: Find all functions that handle 401 responses

```bash
grep -r "401\|WWW-Authenticate\|authenticate" \
  /Users/toddysm/Documents/Development/regshape/src/regshape/libs/ \
  --include="*.py" -l
```

### Q8: Which modules have no internal imports? (leaf nodes in dependency graph)

```bash
python3 -c "
import json
with open('dependencies/dependency-graph.json') as f:
    dep = json.load(f)

forward = dep.get('forward_dependencies', {})
leaf_nodes = [k for k, v in forward.items() if len(v) == 0 and not k.startswith('tests/')]
print('Leaf modules (no internal imports):')
for m in sorted(leaf_nodes):
    print(f'  {m}')
"
```

### Q9: What is the full call chain for `regshape blob push`?

```
Entry: cli/blob.py → push command
  ↓ parse_image_ref() → libs/refs.py
  ↓ RegistryClient(TransportConfig(...)) → libs/transport/client.py
  ↓ resolve_credentials(registry) → libs/auth/credentials.py
      ↓ read_docker_config() → libs/auth/dockerconfig.py
      ↓ exec docker-credential-X → libs/auth/dockercredstore.py
  ↓ push_blob_monolithic(client, ...) → libs/blobs/operations.py
      @track_scenario("push blob")
      @track_time
      ↓ head_blob() → client.head("/v2/repo/blobs/digest")
          → MiddlewarePipeline → AuthMiddleware → HTTP
      ↓ client.post("/v2/repo/blobs/uploads/") → HTTP 202
      ↓ client.put("{upload_url}?digest=...") → HTTP 201
      ↓ return Descriptor(mediaType, digest, size)
  ↓ print telemetry block → libs/decorators/output.py
```

### Q10: Show all error types and where they're raised

```bash
grep -rn "raise \(Auth\|Manifest\|Tag\|Blob\|Catalog\|Referrer\|Layout\)Error" \
  /Users/toddysm/Documents/Development/regshape/src/regshape/libs/ \
  --include="*.py"
```

---

## Useful jq Queries for JSON Files

If you have `jq` installed, these queries work on the scan result files:

```bash
# Count bandit findings by severity
jq '[.results[] | .issue_severity] | group_by(.) | map({severity: .[0], count: length})' \
  security/tool-scan-results/bandit/bandit-results.json

# List all pip-audit vulnerable packages  
jq '.dependencies[] | select(.vulns | length > 0) | {name, version, vuln_count: (.vulns | length)}' \
  security/tool-scan-results/pip-audit/pip-audit-results.json

# List semgrep findings with location
jq '.results[] | {rule: .check_id, file: .path, line: .start.line, severity: .extra.severity}' \
  security/tool-scan-results/semgrep/semgrep-results.json

# Check if detect-secrets found anything
jq '.results | length' \
  security/tool-scan-results/detect-secrets/detect-secrets-results.json
```
