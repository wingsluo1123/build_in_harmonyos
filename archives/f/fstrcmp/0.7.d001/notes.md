# fstrcmp 0.7.D001 (packaged as 0.7.d001) OpenHarmony adaptation

## Source

- Upstream: fstrcmp (fuzzy string compare library) by Peter Miller, home page
  <https://fstrcmp.sourceforge.net/>; this release is `0.7.D001`.
- The recipe uses the Kodi build-deps mirror of this release:
  `https://mirrors.kodi.tv/build-deps/sources/fstrcmp-0.7.D001.tar.gz`
  (394,845 B, sha256 `e4018e850f80700acee8da296e56e15b1eef711ab15157e542e7d7e1237c3476`).
  Three reasons for this choice:
  1. It is byte-identical to the artifact Kodi's own `tools/depends` build
     consumes — the SHA512 recorded in Kodi's `FSTRCMP-VERSION`
     (`aaeb0227…`) matches this tarball exactly.
  2. The repository's PF7/R39 gate rejects Debian-repackaged source URLs in
     conandata, so `fstrcmp_0.7.D001.orig.tar.gz` cannot be declared.
  3. The upstream SourceForge download path answered with an anti-bot HTML
     page from the analysis host, so the official tarball's real size and
     sha256 could not be established there.
  This tarball ships a generated `configure`, so no `autoreconf` is needed.
  For reference, the Debian `_orig` archive (390,208 B) unpacks to the same
  tree without the extra `debian/` directory that this mirror carries.
- Licence: the source headers grant **LGPL-3.0-or-later** ("GNU Lesser General
  Public License ... either version 3 ... or (at your option) any later
  version"), which is what the recipe declares. Note that the top-level
  `LICENSE` file ships the GPL-3 text instead; the per-file grant is treated as
  authoritative for the package. A repository-wide double-check is welcome.

## Adaptation

- Plain autotools. The tarball already ships a generated `configure`, so no
  `autoreconf` is needed.
- `patches/0001-config.sub-ohos.patch` teaches the bundled (pre-HarmonyOS)
  `config.sub` the `aarch64-linux-ohos` triplet: it adds `aarch64` to the CPU
  table and accepts `-linux-ohos` in both the OS alias table and the main OS
  table. Verified locally: `./config.sub aarch64-linux-ohos` prints
  `aarch64-unknown-linux-ohos` (exit 0).
- `generate()` passes `--build/--host=aarch64-linux-ohos` on OHOS.
- `package()` calls only `install-include install-libdir`: the aggregate
  `install` target would additionally install the CLI, man pages and the
  aegis-generated `building.pdf`. Kodi's own `tools/depends` build makes the
  same choice.
- No conan dependencies: the library is self-contained.

## Verification

- `make check` (upstream suite) is run inside `build()`.
- `test_package/fstrcmp_smoke` links against `libfstrcmp` and asserts
  `fstrcmp(x, x) > 0.99` plus the documented `[0, 1]` result range.

## Why this package exists separately

Kodi 21.3 lists `fstrcmp` among its required third-party dependencies, and its
`cmake/modules/FindFstrcmp.cmake` resolves it through pkg-config or
`find_path` + `find_library` (`fstrcmp.h`, `libfstrcmp`). This package provides
exactly those, including `lib/pkgconfig/fstrcmp.pc`, so the Kodi adaptation can
simply `requires("fstrcmp/0.7.D001")` instead of vendoring the library.
