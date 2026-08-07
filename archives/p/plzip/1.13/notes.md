# plzip 1.13 — Adaptation Notes

## Basic Information
- **Software**: plzip
- **Version**: 1.13
- **Status**: built (conan-verify passed)
- **Build System**: custom_configure (custom shell-based configure, not autotools)
- **Source**: https://download.savannah.gnu.org/releases/lzip/plzip/plzip-1.13.tar.gz
- **SHA256**: 64d49dde20daa5fdff2b3ff28e3348082de10dd54eb10df6da7d1bc6c7a6db64

## Key Findings

### Custom Configure Script
- plzip uses a custom configure script (not autoconf-generated)
- The configure script hardcodes `CXX=g++` and falls back to `c++`
- CXX must be passed as a configure argument (`CXX=clang++`), not via environment
- The configure script links with `-llz -lpthread` (lzlib + pthread)

### Dependency
- plzip depends on lzlib (liblz.a)
- Managed through Conan requires: `self.requires("lzlib/1.15")`
- Conan automatically provides include and library paths for lzlib

### Build & Test Results
- `./configure --prefix=... CXX=clang++ CXXFLAGS=-fPIC -O2` → OK
- `make -j1` → OK (builds plzip binary)
- `make check` → PASS (compression, decompression, bad input tests)
- `make install DESTDIR=...` → OK (installs plzip to bin/)

### Package Type
- plzip is an application (command-line tool), not a library
- `package_type = "application"`
- `cpp_info.bindirs = ["bin"]`
- commands.json created at software level (R38)

## 最终状态

- **状态**: built
- **结束时间**: 2026-08-08
- COMPLETED
---

**编译结束**: 2026-08-08 01:28
**最终状态**: built
