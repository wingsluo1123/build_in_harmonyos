# Test Report — lmdbxx 1.0.0

## Compilation Tests

### Header Installation
- `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX` — PASS
- Header `lmdb++.h` (44175 bytes) installed to `include/`

### Upstream Test Suite (make check)
- Command: `make check CPPFLAGS="-I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib"`
- Result: PASS (compiled and ran successfully)
- Test covers: env create/open, put/get, cursor iteration, delete, sorted dups, to_sv/from_sv, nested transactions

## Conan Test Package
- `conan create` with test_package: PASS
- Test covers: env create, db open, put/get, update, cursor, delete
- All assertions passed

## Test Environment
- Compiler: clang 15.0.4
- Platform: OpenHarmony (aarch64)
- lmdb: 0.9.35 (from cmd-pkgs, for local testing)
- conan: 2.29.1 (OHOS adapted)

## Notes
- The `version` file in source directory conflicts with C++17 `<version>` standard header
- Workaround: remove `-I.` from CPPFLAGS (check.cc uses `#include "lmdb++.h"` with quotes)
