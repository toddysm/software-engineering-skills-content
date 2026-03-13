# Security Remediation Guide — Notation Project

**Priority ordering**: Fix highest-impact items first. Each item includes exact file paths, before/after code, and verification steps.

---

## Remediation 1 — Add filepath.Clean() in File Utility Functions

**Severity**: MEDIUM (G304 — File Inclusion via Variable)
**Effort**: 30 minutes
**Finding IDs**: NOTATION-2026-001, NOTATION-2026-002
**File**: `cmd/notation/internal/osutil/file.go`

### Why

The `Copy` and `WriteFile` helpers pass variable-derived paths directly to `os.Open` and `os.WriteFile`. While the current callers provide controlled paths from the `dir` package, adding explicit canonicalization ensures the functions are safe for any future caller.

### Before

```go
// cmd/notation/internal/osutil/file.go

func Copy(src, dst string) error {
    f, err := os.Open(src)
    if err != nil {
        return err
    }
    defer f.Close()
    // ...
}

func WriteFile(path string, data []byte) error {
    if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
        return err
    }
    return os.WriteFile(path, data, WritableFileMode)
}
```

### After

```go
// cmd/notation/internal/osutil/file.go

func Copy(src, dst string) error {
    src = filepath.Clean(src)
    dst = filepath.Clean(dst)
    f, err := os.Open(src)
    if err != nil {
        return err
    }
    defer f.Close()
    // ...
}

func WriteFile(path string, data []byte) error {
    path = filepath.Clean(path)
    if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
        return err
    }
    return os.WriteFile(path, data, WritableFileMode)
}
```

### Verification

```bash
cd /Users/toddysm/Documents/Development/notaryproject/notation
go build ./...
go test ./cmd/notation/internal/osutil/...
gosec -include=G304 ./cmd/notation/internal/osutil/...
# Expected: 0 G304 findings after adding filepath.Clean
```

---

## Remediation 2 — Add filepath.Clean() in Plugin Installer

**Severity**: MEDIUM (G304)
**Effort**: 30 minutes
**Finding ID**: NOTATION-2026-003
**File**: `cmd/notation/internal/plugin/install.go`

### Why

The plugin binary path is constructed from a user-provided plugin name (validated) joined with the libexec directory. Adding `filepath.Clean()` ensures that any edge cases in path construction (double slashes, dots) are normalised before the `os.Lstat` and `os.Open` calls.

### Change

```go
// cmd/notation/internal/plugin/install.go

// Before opening the plugin binary:
pluginPath = filepath.Clean(pluginPath)

// Optionally, add a bounds check:
libexecDir, _ := dir.UserLibexecFS().SysPath("")
if !strings.HasPrefix(pluginPath, filepath.Clean(libexecDir)) {
    return fmt.Errorf("plugin path %q is outside the allowed plugins directory", pluginPath)
}
```

### Verification

```bash
go test ./cmd/notation/internal/plugin/...
gosec -include=G304 ./cmd/notation/internal/plugin/...
```

---

## Remediation 3 — Suppress G115 False Positive with Justification

**Severity**: LOW (G115 — Integer Overflow, False Positive)
**Effort**: 5 minutes
**Finding ID**: NOTATION-2026-004
**File**: `cmd/notation/login.go`, lines 191–192

### Why

Converting `os.Stdin.Fd()` (`uintptr`) to `int` will never overflow because:
1. File descriptors are always small non-negative integers (stdin=0).
2. All notation build targets are 64-bit; `uintptr` and `int` are both 64 bits — no truncation possible.

Adding a `//nolint:gosec` comment documents the reasoning and prevents CI alarm fatigue.

### Before

```go
isTerminal := term.IsTerminal(int(os.Stdin.Fd()))
password, err := term.ReadPassword(int(os.Stdin.Fd()))
```

### After

```go
//nolint:gosec // G115: os.Stdin.Fd() is always a small non-negative int; all targets are 64-bit
isTerminal := term.IsTerminal(int(os.Stdin.Fd()))
//nolint:gosec // G115: same as above
password, err := term.ReadPassword(int(os.Stdin.Fd()))
```

### Verification

```bash
gosec -include=G115 ./cmd/notation/...
# Expected: 0 findings (suppressed by nolint annotation)
```

---

## Remediation 4 — Handle fmt.Fprintf Error Returns for Critical Output

**Severity**: INFO/Code Quality (G104 — Errors Unhandled)
**Effort**: 2–4 hours
**Finding ID**: NOTATION-2026-005
**Files**: Multiple `cmd/notation/*.go` files

### Why

While writing to stdout/stderr rarely fails in practice, Go's idiom is to check error returns. For final result lines that communicate success/failure to the caller, unhandled write errors can silently lose output. For incidental output (warnings, progress), suppression with annotation is appropriate.

### Strategy

**Tier 1 — Final Result Lines**: Check error, return/log if write fails.

```go
// Before (sign.go — final success message):
fmt.Fprintf(cmd.OutOrStdout(), "Successfully signed %s\n", ref)

// After:
if _, err := fmt.Fprintf(cmd.OutOrStdout(), "Successfully signed %s\n", ref); err != nil {
    return fmt.Errorf("failed to write output: %w", err)
}
```

**Tier 2 — Warning/Informational Lines**: Annotate to suppress.

```go
// Before (incidental warning):
fmt.Fprintf(os.Stderr, "Warning: certificate chain has %d cert(s)\n", count)

// After:
_, _ = fmt.Fprintf(os.Stderr, "Warning: certificate chain has %d cert(s)\n", count) //nolint:errcheck
```

### Verification

```bash
gosec -include=G104 ./cmd/notation/...
# Expected: 0 findings after addressing all 28 instances
```

---

## Remediation 5 — Add Security Scanners to CI Pipeline

**Severity**: Process Improvement
**Effort**: 1–2 days
**File**: `.github/workflows/build.yml` or a new `.github/workflows/security.yml`

### Why

`semgrep` and `gitleaks` were not available on the analysis host. Adding them to CI ensures ongoing coverage for secret detection (gitleaks) and custom taint/pattern rules (semgrep).

### Suggested CI Step (GitHub Actions)

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: ["main", "release-*"]
  pull_request:

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # required for gitleaks history scan

      - name: Run gosec
        uses: securego/gosec@master
        with:
          args: '-fmt=sarif -out=gosec.sarif ./...'

      - name: Upload gosec results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: gosec.sarif

      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Run semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/golang
            p/owasp-top-ten
            p/supply-chain
```

### Verification

After merging, confirm all three scan steps pass in the GitHub Actions UI. Address any new findings from semgrep/gitleaks before considering the pipeline stable.

---

## Summary Checklist

| # | Remediation | File(s) | Effort | Status |
|---|------------|---------|--------|--------|
| 1 | Add `filepath.Clean()` in osutil | `osutil/file.go` | 30 min | ⬜ |
| 2 | Add `filepath.Clean()` + bounds check in plugin installer | `plugin/install.go` | 30 min | ⬜ |
| 3 | Suppress G115 with `//nolint:gosec` + justification | `login.go` | 5 min | ⬜ |
| 4 | Handle or annotate G104 `fmt.Fprintf` returns | Multiple | 2–4 hrs | ⬜ |
| 5 | Add semgrep + gitleaks to CI | `.github/workflows/` | 1–2 days | ⬜ |
