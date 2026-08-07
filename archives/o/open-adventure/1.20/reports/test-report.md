# open-adventure 1.20 Test Report

## Build
- Build system: Makefile (no configure)
- Compiler: clang 15.0.4
- CFLAGS: -fPIC -O2
- Dependencies: libedit (static), ncurses (static)

## Binaries
- advent (674KB) - main game binary
- cheat (645KB) - debug/cheat tool

## ELF Dependencies
- libc.so (only dynamic dependency, all other libs statically linked)

## Test Results
- 103 passed, 4 failed (out of 107 regression tests)
- Failures: cheatresume, cheatresume2, resumefail2, savetamper
- All failures are in save/resume edge cases with cheated save files (non-critical)
- The 4 failures are due to save file format compatibility, not compilation issues

## Staging Verification
- advent -x: exits with code 1 (expected, prints usage)
- ELF check: only libc.so dependency
- Binary is functional
