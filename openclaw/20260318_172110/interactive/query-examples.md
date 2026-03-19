# Dependency Query Examples — OpenClaw

This document provides example queries you can answer using the dependency data in this analysis.

---

## Using the Query Database

The file `dependency-query-db.json` contains pre-computed answers to common dependency questions. For deeper queries, use the raw data in `../dependencies/`.

---

## Quick Answers from Query Database

### Q: What are the most imported files in the codebase?

Look at `most_depended_on` in `dependency-query-db.json`. These files are the most critical — changes to them have the widest blast radius.

### Q: What files have the most dependencies?

Look at `most_dependencies`. These are the most complex files — they depend on many other modules and are likely hardest to refactor.

### Q: Are there hub files (both heavily imported AND heavily importing)?

Look at `hub_files`. These are architecturally significant files that both provide and consume many interfaces. They're natural candidates for refactoring if they grow too large.

### Q: How do modules connect to each other?

Look at `module_connections`. This shows the number of import edges between top-level modules (e.g., `src/gateway` → `src/agents`, `extensions/` → `src/channels`).

### Q: Are there circular dependencies?

Look at `circular_dependencies`. The analysis found 1 circular dependency:
- `ui/src/ui/app-settings.ts` ↔ `ui/src/ui/app-chat.ts`

---

## Deeper Queries (Using Raw Data)

### Q: "What would break if I changed file X?"

Use `../dependencies/impact-analysis.json`. Look up file X to see all files that transitively depend on it.

### Q: "What does file X depend on?"

Use `../dependencies/dependency-graph.json`. Look up file X → `imports_from` to see direct dependencies, and `imported_by` to see reverse dependencies.

### Q: "What functions does file X export?"

Use `../dependencies/dependency-graph.json`. Look up file X → `functions_providing` for exported functions, and `functions_used` for consumed functions.

### Q: "What functions are defined in the project?"

Use `../source-files/function-catalog.json` for a comprehensive catalog of all functions, classes, and methods across all files.

---

## Example: Tracing a Message Through the System

To understand how a Discord message reaches an LLM provider:

1. **Entry:** `extensions/discord/runtime.ts` receives message
2. **Look up:** `dependency-graph.json["extensions/discord/runtime.ts"]["imports_from"]`
3. **Follow:** Through `src/channels/session.ts` → `src/gateway/server.impl.ts` → `src/agents/pi-tools.ts`
4. **Terminal:** `extensions/openai/runtime.ts` sends to LLM

Each hop can be verified by checking the file's `imports_from` and `imported_by` fields.

---

## Example: Finding All Files in a Module

```python
import json

with open("dependency-query-db.json") as f:
    db = json.load(f)

# Show which modules connect to src/gateway
for module, targets in db["module_connections"].items():
    if "src/gateway" in targets:
        print(f"{module} → src/gateway: {targets['src/gateway']} edges")
```

---

## Data File Reference

| File | Size | Contents |
|------|------|----------|
| `dependency-query-db.json` | ~50KB | Pre-computed query answers |
| `../dependencies/dependency-graph.json` | ~8MB | Full file-to-file dependency graph (12,136 entries) |
| `../dependencies/function-dependencies.json` | ~21MB | Function-level dependency data |
| `../dependencies/impact-analysis.json` | ~1.3MB | Transitive impact analysis |
| `../dependencies/circular-dependencies.json` | ~1KB | Detected circular dependencies |
| `../source-files/file-inventory.json` | varies | All files with metadata |
| `../source-files/function-catalog.json` | varies | All functions/classes/methods |
