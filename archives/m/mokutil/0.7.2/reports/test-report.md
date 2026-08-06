# mokutil 0.7.2 — Test Report

## Build Test
- Build system: Custom (direct compilation, autotools source but automake unavailable on OHOS)
- Compiler: clang 15.0.4
- Build result: SUCCESS
- Binary built: mokutil
- Source files compiled: mokutil.c, efi_hash.c, efi_x509.c, keyring.c, password-crypt.c, util.c, musl_shim.c

## Conan Package Test
- conan create: PASS
- test_package: PASS
- Test output: "0.7.2" (mokutil --version)

## Dependencies
- openssl/3.5.6 (from conan remote)
- efivar/39 (local conan package)
- keyutils/1.6.1 (local conan package)

## Patches Applied
1. 0001-configure.ac.patch — remove -fshort-wchar
2. 0002-src-Makefile.am.patch — add musl_shim.c/h to sources
3. 0003-src-mokutil.c.patch — replace #include <shadow.h>
4. 0004-src-musl_shim.c.patch — new file: l64a/getspnam compat
5. 0005-src-musl_shim.h.patch — new file: declarations

## Platform Issues Resolved
- -fshort-wchar: incompatible with musl wchar_t → removed
- l64a(): GNU extension not in musl → custom implementation
- getspnam(): GNU extension not in musl → returns NULL (no shadow passwords)
- automake: not available on OHOS → direct compilation bypassing autotools

## Test Date: 2026-08-06
## Final Status: built
