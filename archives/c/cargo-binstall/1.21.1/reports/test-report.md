# Test Report — cargo-binstall 1.21.1

## Build & Package

| Check | Result |
|-------|--------|
| conan create | ✅ PASS |
| Package files | cargo-binstall, detect-targets, detect-wasi, LICENSE, README.md |
| ELF signing | ✅ All 3 binaries signed via binary-sign-tool |

## Test Results

### test_package (Conan L1)

| Test | Command | Expected | Actual | Result |
|------|---------|----------|--------|--------|
| Version check | `cargo-binstall -V` | `1.21.1` | `1.21.1` | ✅ PASS |
| Target detection | `detect-targets` | Contains `aarch64` | `aarch64-unknown-linux-musl` | ✅ PASS |
| WASI detection | `detect-wasi` | Non-empty output | `WASI is not runnable` | ✅ PASS |
| Help output | `cargo-binstall --help` | Contains usage info | `Install a Rust binary... from binaries!` | ✅ PASS |

### conan-verify Gates

| Gate | Description | Result |
|------|-------------|--------|
| G1 | Recipe completeness | ✅ PASS |
| G2 | conan create (clean build) | ✅ PASS |
| G3 | System library isolation (R26) | ✅ PASS |
| G4 | Product completeness | ✅ PASS |
| L2 | Smoke test (--version) | ✅ PASS |
| L4 | Security scan (NX/PIE/RELRO) | ✅ PASS |
| L5 | Baseline artifact check | ✅ PASS |

### W3 Local CI Simulation

| Step | Result |
|------|--------|
| setup.sh | ✅ PASS |
| build_and_test.sh | ✅ PASS |

## Summary

All 4 smoke tests passed. All 7 conan-verify gates passed. Local CI simulation passed.

**Final status: published**
