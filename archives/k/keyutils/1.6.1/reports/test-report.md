# keyutils 1.6.1 — Test Report

## Build Test
- Build system: Makefile
- Compiler: clang 15.0.4
- Build result: SUCCESS
- Libraries built: libkeyutils.so, libkeyutils.a
- Binaries built: keyctl, request-key, key.dns_resolver

## Conan Package Test
- conan create: PASS
- test_package: PASS
- Test output: "keyutils test: thread keyring spec = -1"

## Patches Applied
1. 0001-fix-musl-rindex-index.patch — replace rindex→strrchr, index→strchr

## Platform Issues Resolved
- rindex(): BSD function not in musl → replaced with strrchr()
- index(): BSD function not in musl → replaced with strchr()

## Test Date: 2026-08-06
## Final Status: built
