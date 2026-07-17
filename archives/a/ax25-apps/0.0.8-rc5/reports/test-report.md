# Test Report — ax25-apps 0.0.8-rc5

**Date**: 2026-07-17  
**Status**: PASS  

## Build Verification
- configure: PASS (all checks passed)
- make: PASS (all 6 binaries compiled)
- make install: PASS (all binaries installed)
- make check: PASS (no test suite, nothing to check)

## Conan Verification
- conan-verify: PASS (8 gates all passed)
- W3 local CI simulation: PASS (setup.sh + build_and_test.sh)

## Functional Tests
- See functional-test-report.md for detailed results
- All 6 binaries verified as ELF64 AArch64
- ax25ipd --version: PASS (exit 0, version 0.0.8-rc5)
- ax25rtctl --version: PASS (exit 0, version 0.0.8-rc5)
- ax25mond --version: PASS (version 0.0.8-rc5)
- call/listen: Show usage on unrecognized option (expected)
- ax25rtd: Tries to configure AX.25 ports (expected failure without hardware)

## Summary
All tests pass. Build is verified and ready for submission.
