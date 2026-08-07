# lzlib 1.15 — Adaptation Notes

## Basic Information
- **Software**: lzlib
- **Version**: 1.15
- **Status**: built (conan-verify passed)
- **Build System**: custom_configure (custom shell-based configure, not autotools)
- **Source**: https://download.savannah.gnu.org/releases/lzip/lzlib/lzlib-1.15.tar.gz
- **SHA256**: 4afab907a46d5a7d14e927a1080c3f4d7e3ca5a0f9aea81747d8fed0292377ff

## Key Findings

### Custom Configure Script
- lzlib uses a custom configure script (not autoconf-generated)
- The configure script hardcodes `CC=gcc` and falls back to `CC=cc`
- CC must be passed as a configure argument (`CC=clang`), not via environment
- The configure script supports `--enable-shared` / `--disable-static` but NOT `--enable-static` / `--disable-shared`
- Default build is static-only (liblz.a)

### Library Name
- The library file is `liblz.a` (not `liblzlib.a`)
- `libname=lz` in configure script
- conanfile.py `cpp_info.libs = ["lz"]`

### Build & Test Results
- `./configure --prefix=... CC=clang CFLAGS=-fPIC -O2` → OK
- `make -j1` → OK (builds liblz.a, minilzip, bbexample, ffexample, lzcheck)
- `make check` → PASS (compression, decompression, bad input tests)
- `make install DESTDIR=...` → OK (installs liblz.a, lzlib.h, lzlib.info)
- conan create → PASS
- conan-verify (G0-G4, L2/L4/L5) → PASS

### Conan Recipe
- No patches needed
- No dependencies
- Static library only (shared option available via --enable-shared)
