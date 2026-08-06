# Test Report: icoutils 0.32.3

## Build Information
- Software: icoutils 0.32.3
- Build System: autotools
- Build Date: 2026-08-06
- Compiler: clang 15.0.4
- Platform: HarmonyOS aarch64

## Build Steps

1. **Configure**: `./configure --prefix=$DEFAULT_PREFIX` (with config.guess fix, umask fix)
2. **Compile**: `make -j2` — 8 seconds, 48 warnings (all in system headers, non-fatal)
3. **Install**: `make install DESTDIR=$TEST_PREFIX` — 4 executables + 4 man pages
4. **Test**: `make check` — no automated test suite (icoutils has no test targets)

## Smoke Tests

### Binary Version Checks
```
$ icotool --version
icotool (icoutils) 0.32.3
Copyright (C) 1998 Oskar Liljeblad

$ wrestool --version
wrestool (icoutils) 0.32.3
Copyright (C) 1998 Oskar Liljeblad
```

### Installed Artifacts
| File | Size | Type |
|------|------|------|
| bin/icotool | 84KB | executable |
| bin/wrestool | 68KB | executable |
| bin/extresso | script | executable |
| bin/genresscript | script | executable |
| share/man/man1/*.1 | — | man pages |

## Conan Verification (conan-verify)

| Gate | Name | Result |
|------|------|--------|
| G0 | Pre-build risk assessment | PASS |
| G1 | Recipe completeness | PASS |
| G2 | conan create (clean build) | PASS |
| G3 | System-lib isolation (R26) | PASS |
| G4 | Product integrity | PASS |
| L2 | Smoke test | PASS |
| L4 | Security scan (checksec) | PASS |
| L5 | Product baseline | PASS |

## W3 Local CI Simulation
- setup.sh: PASS
- build_and_test.sh: PASS

## Conclusion
icoutils 0.32.3 builds and runs successfully on HarmonyOS aarch64.
All 4 command-line tools are functional. Conan recipe verified.
