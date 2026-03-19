# Remediation Guide — OpenClaw

Prioritized remediation steps organized by urgency and effort.

---

## Priority 1: Immediate (Fix before next release)

### 1.1 Update fast-xml-parser (CRITICAL) — Est. effort: Low

**CVEs:** CVE-2026-25896, CVE-2026-33036, CVE-2026-26278  
**Current:** 4.5.3 → **Target:** ≥4.5.4 (partial fix), ≥5.5.6 (complete)

```bash
# Check which packages depend on fast-xml-parser
pnpm why fast-xml-parser

# Update to latest patch
pnpm update fast-xml-parser --recursive

# If major version update needed, check breaking changes
pnpm update fast-xml-parser@^5.5.6 --recursive
```

**Verification:** Run `pnpm list fast-xml-parser --recursive` and confirm version ≥4.5.4. Run existing tests to validate no regressions.

---

### 1.2 Update node-forge (HIGH) — Est. effort: Low

**CVEs:** CVE-2025-12816, CVE-2025-66031  
**Current:** 1.3.1 → **Target:** ≥1.3.2

```bash
pnpm update node-forge --recursive
```

**Verification:** Test any TLS/certificate handling code paths.

---

### 1.3 Update jws (HIGH) — Est. effort: Low

**CVE:** CVE-2025-65945  
**Current:** 3.2.2 / 4.0.0 → **Target:** 3.2.3 / 4.0.1

```bash
pnpm update jws --recursive
```

**Verification:** Test JWT/token generation and verification.

---

### 1.4 Implement Secrets Redaction in Logging (HIGH) — Est. effort: Medium

**File:** Create `src/infra/logging/secrets-filter.ts`

```typescript
// Conceptual implementation
const SECRET_PATTERNS = [
  /sk-[a-zA-Z0-9]{20,}/g,          // OpenAI keys
  /xai-[a-zA-Z0-9]{20,}/g,         // xAI keys
  /AIza[a-zA-Z0-9_-]{35}/g,        // Google API keys
  /Bearer\s+[a-zA-Z0-9._-]+/gi,    // Bearer tokens
  /Basic\s+[a-zA-Z0-9+/=]+/gi,     // Basic auth
  /[a-f0-9]{32,}/gi,               // Long hex strings (API keys)
];

export function redactSecrets(message: string): string {
  let redacted = message;
  for (const pattern of SECRET_PATTERNS) {
    redacted = redacted.replace(pattern, '[REDACTED]');
  }
  return redacted;
}
```

**Integration points:**
1. Wrap all `console.log`, `console.error`, and custom logger calls
2. Apply to error messages passed to users
3. Apply to command execution output in bash-tools

---

## Priority 2: Short-term (Fix within 30 days)

### 2.1 Expand Command Injection Detection (HIGH) — Est. effort: Medium

**File:** `src/agents/bash-tools.exec.ts`

**Current state:** `validateScriptFileForShellBleed()` checks for simple patterns.

**Recommended changes:**
1. Add checks for shell metacharacters: `$()`, backticks, `$(())`, `<()`, `|`, `&&`, `;`
2. Validate the command doesn't contain known dangerous binaries: `curl | bash`, `wget -O - | sh`
3. Consider using `execFile()` with argument arrays instead of `exec()` with shell strings where possible:

```typescript
// Before (vulnerable)
exec(`/bin/bash ${scriptPath}`, options);

// After (safer when args are separable)
execFile('/bin/bash', [scriptPath], { ...options, shell: false });
```

---

### 2.2 Extend node.invoke Sanitization (HIGH) — Est. effort: Medium

**File:** `src/gateway/node-invoke-sanitize.ts`

**Current state:** Only `system.run` commands are sanitized.

**Recommended changes:**
1. Define allowed command schemas for all node.invoke operations
2. Validate all parameters against schemas before forwarding
3. Log attempts to use unknown commands

```typescript
const ALLOWED_COMMANDS: Record<string, ZodSchema> = {
  'system.run': systemRunSchema,
  'file.read': fileReadSchema,
  // ... enumerate all legitimate commands
};

function sanitizeNodeInvoke(command: string, params: unknown) {
  const schema = ALLOWED_COMMANDS[command];
  if (!schema) {
    throw new Error(`Unknown node.invoke command: ${command}`);
  }
  return schema.parse(params); // Zod validation
}
```

---

### 2.3 Make Rate Limit Loopback Exemption Configurable (HIGH) — Est. effort: Low

**File:** `src/gateway/auth-rate-limit.ts`

```typescript
// Add to config schema
rateLimiting: {
  exemptLoopback: z.boolean().default(true),
  // When behind a reverse proxy, set to false
}

// In rate limiter
if (config.rateLimiting.exemptLoopback && isLoopback(ip)) {
  return next();
}
```

---

### 2.4 Add DNS Pinning for SSRF Protection (HIGH) — Est. effort: Medium

**File:** `src/infra/net/ssrf.ts`

```typescript
import { lookup } from 'node:dns/promises';

async function resolveAndValidate(hostname: string): Promise<string> {
  const result = await lookup(hostname);
  const ip = result.address;
  
  // Validate the resolved IP (not the hostname)
  if (isPrivateIP(ip) || isLoopbackIP(ip)) {
    throw new Error(`SSRF: resolved to blocked IP ${ip}`);
  }
  
  return ip; // Use this IP directly in the request
}
```

---

## Priority 3: Long-term (Architectural improvements)

### 3.1 Plugin Sandboxing — Est. effort: High

**Goal:** Isolate plugins from gateway process

**Options (in order of recommendation):**
1. **Worker threads** with `worker_threads.Worker` and limited `transferList`
2. **V8 isolates** via `isolated-vm` package
3. **Subprocess isolation** with IPC

**Design considerations:**
- Plugins need selective access to gateway APIs (messaging, config)
- Define a capability-based permission model
- Allow plugins to declare required permissions in manifest

### 3.2 Unified Tool Policy Engine — Est. effort: Medium

**Goal:** Replace overlapping policy layers with single evaluation path

**Approach:**
1. Define policy priority hierarchy
2. Implement explicit merge semantics (deny-overrides, permit-overrides)
3. Add policy decision logging

### 3.3 Formal Threat Model — Est. effort: Medium

**Goal:** Document all trust boundaries, data flows, and threat actors

**Recommended framework:** Microsoft STRIDE or OWASP Threat Modeling

### 3.4 CI/CD Dependency Scanning — Est. effort: Low

Add to GitHub Actions:

```yaml
- name: Security scan
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'
```

---

## Verification Checklist

After applying fixes, verify:

- [ ] All dependency CVEs resolved (`trivy fs .` returns 0 CRITICAL/HIGH)
- [ ] Secrets redaction working (test with fake API key in log output)
- [ ] Rate limiting works behind reverse proxy
- [ ] SSRF protection validated with DNS rebinding test
- [ ] Command injection tests added to test suite
- [ ] Plugin loading still works after any sandboxing changes
- [ ] Node.invoke parameter validation doesn't break existing commands
