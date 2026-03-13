# Interactive Dependency Query Examples

Use `jq` to query the `dependency-query-db.json` file for specific information about the Notation project's dependencies and components.

```bash
DB="dependency-query-db.json"
```

---

## Component Queries

### List all components by tier

```bash
jq '.components | sort_by(.tier) | .[] | "\(.tier). \(.id) (\(.type)) — \(.description)"' "$DB"
```

**Expected output**:
```
"4. notation-plugin-framework-go (library) — Plugin protocol SDK..."
"3. notation-core-go (library) — Cryptographic envelope layer..."
"2. notation-go (library) — High-level signing and verification library..."
"1. notation-cli (cli-binary) — Main CLI binary..."
```

---

### Get all CLI commands

```bash
jq '.components[] | select(.id == "notation-cli") | .cli_commands[]' "$DB"
```

---

### Which packages does notation-go export as key interfaces?

```bash
jq '.components[] | select(.id == "notation-go") | .key_interfaces' "$DB"
```

---

## Dependency Queries

### What does the notation CLI directly import from notation-go?

```bash
jq '.dependencies.repo_level[] | select(.from == "notation-cli" and .to == "notation-go") | .imported_packages' "$DB"
```

---

### Which repositories depend on notation-core-go?

```bash
jq '.dependencies.repo_level[] | select(.to == "notation-core-go") | .from' "$DB"
```

---

### Show all external dependencies with security relevance

```bash
jq '[.dependencies.external[] | select(.security_relevant == true) | {package, cve_count, notes}]' "$DB"
```

---

### Show all external dependencies with known CVE count > 0

```bash
jq '[.dependencies.external[] | select(.cve_count > 0) | .package]' "$DB"
```

**Expected output**: `[]` (no CVEs found)

---

### Which external packages does each internal repo use?

```bash
jq '[.dependencies.external[] | {package: .package, used_by: .used_by[]}] | group_by(.used_by) | .[] | {repo: .[0].used_by, packages: [.[].package]}' "$DB"
```

---

## Impact Analysis Queries

### What happens if I change the plugin protocol?

```bash
jq '.impact_matrix[] | select(.change_in | contains("plugin-framework"))' "$DB"
```

---

### List all changes that have HIGH impact

```bash
jq '[.impact_matrix[] | select(.impact | startswith("HIGH")) | {change: .change_in, affects: .affects}]' "$DB"
```

---

### Show impact sorted by tier depth (deepest change = largest blast radius)

```bash
jq '[.impact_matrix | sort_by(.tier_depth) | reverse | .[] | {change: .change_in, tier: .tier_depth, impact: .impact}]' "$DB"
```

---

### What is the blast radius of changing the Envelope interface?

```bash
jq '.impact_matrix[] | select(.change_in | contains("Envelope")) | "Affects: \(.affects | join(", "))\nImpact: \(.impact)"' "$DB"
```

---

## Security Queries

### Show all security-relevant external dependencies

```bash
jq '[.dependencies.external[] | select(.security_relevant == true) | {package, cve_count, purpose, notes}]' "$DB"
```

---

### Get the overall project CVE count

```bash
jq '[.dependencies.external[] | .cve_count] | add' "$DB"
```

**Expected output**: `0`

---

### Find any dep that processes attacker-controlled input

```bash
jq '.dependencies.external[] | select(.notes != null and (.notes | contains("attacker"))) | .package' "$DB"
```

---

## Metadata Queries

### When was this analysis generated?

```bash
jq '.metadata.generated_at' "$DB"
```

---

### How many components are in the project?

```bash
jq '.components | length' "$DB"
```

---

### How many external dependencies are tracked?

```bash
jq '.dependencies.external | length' "$DB"
```

---

## One-Liner: Full Security Summary

```bash
jq '"Total components: \(.components | length)\nExternal deps: \(.dependencies.external | length)\nSecurity-relevant deps: \([.dependencies.external[] | select(.security_relevant == true)] | length)\nTotal CVEs: \([.dependencies.external[] | .cve_count] | add)\nHigh-impact changes: \([.impact_matrix[] | select(.impact | startswith("HIGH"))] | length)"' "$DB"
```
