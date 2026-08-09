# Test Report — hwinfo 25.2

## Build
- Build system: Makefile
- Compiler: clang 15
- Platform: OHOS aarch64
- Status: PASS

## Test Results
- `hwinfo --version`: outputs "25.2" — PASS
- conan test_package: PASS (L1a/L1b/L1e verified)
- L2 smoke test: PASS
- L4 security scan: PASS
- L5 baseline check: PASS

## Notes
- Pre-generated hd_ids.h patches skip the slow check_hd --check --sort step
- Platform fixes: ohos_fixup.h, version.h, ISDN.CDB.txt, lex→flex
