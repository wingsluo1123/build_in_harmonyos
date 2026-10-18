# wit 3.01a — build notes

## Upstream

- Wiimms ISO Tools v3.01a (2017-12-03, revision 7464), GPL-2.0. The author's
  site https://wit.wiimm.de/ no longer serves release tarballs (soft 404 on
  every candidate URL), so the source is taken from the Debian source package
  archive. `wit_3.01a.orig.tar.gz` (sha256 in conandata.yml) is byte identical
  to the file referenced by the Debian archive and is the same tarball Debian
  builds from.
- The Debian tarball is a repack: Debian stripped the bundled `libbz2` copy
  and the OpenSSL based crypto helpers from the pristine upstream tarball.
  This recipe therefore follows the Debian patch route and links bzip2/mhash
  from Conan packages instead of restoring the stripped sources.

## Build

- Build system: plain GNU make, targets `wit wwt wdf` build the three user
  tools (no `ar` involved; objects link straight into the binaries).
- `setup.sh` is an interactive host detection script that writes
  `Makefile.setup` at build time. It cannot run while cross compiling:
  patch 0001 adds a `WIT_SETUP_SKIP=1` guard and the recipe writes a fixed
  `Makefile.setup` (revision 7464, date 2017-12-03, `SYSTEM=linux`,
  `HAVE_ZLIB=1`, static build off) instead. `WIT_SETUP_SKIP` must be in the
  make *environment* because setup.sh runs inside a `$(shell)` context which
  does not inherit make command line variables.
- `SYSTEM=linux` avoids `makefiles-local/Makefile.local.x86_64`
  (adds `-march=x86-64`) and matches what `system.c` detects for a linux
  build; there is no `Makefile.local.linux`.
- All pre-generated UI sources ship in `src/ui/` (`ui-*.c/h`, `tab-*.inc`,
  `gen-ui.c`), so no generator step runs at build time; `gen-ui` is compiled
  and linked but never executed.
- Compiler injection (validated in a local cross build):
  `CC` from `tools.build:compiler_executables`, `STRIP=true`,
  `XFLAGS="-fPIE -I<zlib> -I<bzip2> -I<mhash>"`,
  `LDFLAGS="-pie -L<zlib> -L<bzip2> -L<mhash>"` on the make command line.
  `XFLAGS` is the Makefile's designed `CFLAGS` injection point.
- The Makefile hardcodes `SHELL = /usr/bin/env bash`; the `SHELL` from the
  profile build environment is passed on the make command line when the path
  exists, so the build uses the profile bash even without `/usr/bin/env`.
- Dependencies and their roles: zlib (WIA compression), bzip2 (WIA/bzip2
  streams), mhash (SHA-1). Patch 0002 (adapted from Debian
  `use-libbz2-and-mhash`) drops the bundled bzip2 and OpenSSL-SHA1 code,
  adds `src/wit-sha1.c` (SHA-1 through mhash) and links `-lbz2 -lmhash`;
  the bundled lzma decoder is kept because nothing replaces it.

## Environment notes (local cross runner; not package defects)

- Local smoke runs execute the aarch64 binaries through qemu-user with the
  OHOS musl loader shim. The local loader lacks `__fd_chk`, which real OHOS
  libc exports, so `LD_PRELOAD` of a small shim library is needed on this
  runner only (`LD_PRELOAD=<ohos-run>/lib/libfdchkshim.so`). On the OHOS
  device the binaries run natively without any preload.
- musl based OHOS libc declares `stdout`/`stderr` as `const FILE *`;
  patch 0003 adds a `set_std_stream()` helper to dclib-color.c used at the
  four restore/redirect sites.

## Consumer tests

- Upstream ships no runnable test suite: the `wtest` tool in the tarball
  requires the private, unpublished "work" sources (`wtest+.c`,
  `HAVE_WORK_DIR`); Debian runs no tests either. Therefore
  `test_package/test_wit.sh` crafts minimal fixtures itself:
  - a 64 KiB raw Wii disc image (disc id + Wii/GameCube magic words) and a
    hand built WDF v1 container wrapping it, plus a non-disc control file;
  - asserts version banners of wit/wwt/wdf (`v3.01a r7464`), ELF64/LE/
    AArch64/PIE headers, `wit FTYPE` magic based classification
    (ISO/WII, WDF1/WII, OTHER, NO-FILE), `wdf +DUMP` structure parsing
    (WDF version 1, one data chunk), a byte exact `wdf +CAT` payload
    roundtrip (sha256 comparison) and the `wdf +DUMP` error path on a
    missing file (exit code 76).
- Deep WIA/bzip2/SHA-1 code paths are linked (package requirements) but not
  exercised by the consumer tests; exercising them would require full Wii
  disc images.
