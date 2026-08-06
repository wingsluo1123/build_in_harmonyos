# libtheora

Theora video codec library packaged from the official Xiph.Org release.

Theora is a free, patent-unencumbered video codec derived from On2's VP3 codec,
developed by the Xiph.Org Foundation. This package provides static libraries
(theora, theoradec, theoraenc) built with CMake for HarmonyOS PC (aarch64).

- **Homepage**: https://xiph.org/theora/
- **License**: BSD-3-Clause
- **Language**: C

## Available versions

| Version | Status | Build system | Notes |
|---------|--------|-------------|-------|
| 1.1.1   | built  | cmake       | Custom CMakeLists.txt replaces autotools; requires libogg/1.3.6 |

## 1.1.1 version notes

### Dependencies
- libogg (1.3.6 or compatible) — from ohpcd conan remote

### Build configuration (HarmonyOS aarch64)
The upstream source uses autotools (configure.ac, Makefile.am) which fails on
HarmonyOS due to TMPDIR permission issues and unrecognised platform. A custom
CMakeLists.txt replaces the autotools build system for cross-compilation:

```bash
conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```

### Libraries
| Library | Description |
|---------|-------------|
| libtheoradec.a | Theora decoder library |
| libtheoraenc.a | Theora encoder library (includes mcenc.c for motion estimation) |
| libtheora.a    | Combined decoder + encoder library |

### Headers
- `theora/codec.h` — base codec types
- `theora/theora.h` — legacy API
- `theora/theoradec.h` — decoder API
- `theora/theoraenc.h` — encoder API

### Pkg-config files
- `theora.pc`, `theoradec.pc`, `theoraenc.pc`
