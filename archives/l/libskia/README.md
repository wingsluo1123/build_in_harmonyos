# libskia (Skia)

[Skia](https://skia.org) is an open-source 2D graphics library that provides
 APIs for text, geometry, and images on a canvas. It is the graphics engine
 used by Chrome, Android, Flutter, and others.

This archive packages Google Skia for HarmonyOS PC (aarch64).

- Upstream: https://skia.googlesource.com/skia (mirror https://github.com/google/skia)
- License: BSD-3-Clause

## Versions

| Version | Upstream | Status |
|---|---|---|
| 146.20260602-git.3476902 | chrome/m146 @ `34769028da93df54a2e33ebe8985413924053bc1` (2026-06-02) | local-prep draft |

## Build notes

Skia uses **GN + ninja** (not CMake). The release tarball excludes its bundled
third-party sources; the recipe fetches them via `tools/git-sync-deps` and
bootstraps `gn`/`ninja` via `bin/fetch-gn`/`bin/fetch-ninja`. The first OHOS
build targets a static, GPU-free software rasterizer. See the version-level
`notes.md` for open blockers and next commands.
