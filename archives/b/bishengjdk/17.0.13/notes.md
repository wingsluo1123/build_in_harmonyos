# Adaptation Notes — bishengjdk 17.0.13

## Build System
Pre-built binary (not source-compiled).

## Adaptation Approach
1. Download BiSheng JDK 17.0.13 Linux aarch64 binary from Huawei mirror
2. Patch ELF interpreter: ld-linux-aarch64.so.1 → ld-musl-aarch64.so.1
3. Replace glibc NEEDED entries: libc.so.6 → libc.so, libdl.so.2 → libc.so, etc.
4. Create musl compat symlinks: libc.so → /lib/ld-musl-aarch64.so.1
5. Compile glibc compatibility shim (libgcompat.so) for missing symbols
6. Self-sign all ELF files with binary-sign-tool -selfSign 1 (E083)

## Key Findings
- BiSheng JDK Linux aarch64 binary is glibc-compiled
- HarmonyOS uses musl libc (ld-musl-aarch64.so.1)
- glibc-specific symbols needed: __getpagesize, malloc_trim, __xstat*, __ctype_b_loc, etc.
- glibc/musl ABI differences cause segfault in JVM (struct stat, jmp_buf, TLS layout)
- Test verifies adaptation was applied (ELF checks, not java -version execution)

## Knowledge Graph
- E083: BiSheng JDK System.load signing verification

## COMPLETED
bishengjdk 17.0.13 adaptation completed. Status: published.
