# Test Report — re2c 4.3.1

## Build Information
- Software: re2c 4.3.1
- Build System: CMake
- Platform: OHOS aarch64
- Compiler: clang 15.0.4
- Build Date: 2026-08-08

## Build Result
- CMake configure: ✅ PASS (with HarmonyOS platform warnings, non-fatal)
- Make build: ✅ PASS (12 executables built + 5 test binaries)
- Make install: ✅ PASS (24 files installed)

## Binary Verification
- `re2c --version`: ✅ returns "re2c 4.3.1"
- `re2c --help`: ✅ shows usage

## Conan Verification
- G1 (recipe completeness): ✅ PASS
- G0 (pre-build risk): ✅ PASS
- G2 (conan create clean build): ✅ PASS
- G3 (system library isolation): ✅ PASS
- G4 (product completeness): ✅ PASS

## Test Package
- re2c processes .re input and generates C code: ✅
- Generated C code compiles and runs: ✅
- Test output: "re2c test: scan result=1 (expected 1)"

## Upstream Test Suite
- `python3 run_tests.py`: ⚠️ FAILED (platform limitation: `chmod` not found via Python posix_spawn)
- This is a Python platform issue, not a re2c build issue

## W3 Local CI Simulation
- setup.sh: ✅ PASS
- build_and_test.sh: ✅ PASS (L0-L5 quality gates passed)

## Notes
- re2c is a command-line tool (lexer generator), not a library
- No external dependencies required
- CMake build system chosen over autotools due to config.status permission issues on OHOS
- Autotools config.guess/config.sub patched for OHOS support (for future autotools users)
