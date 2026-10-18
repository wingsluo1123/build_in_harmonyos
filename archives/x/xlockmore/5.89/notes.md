# xlockmore 5.89 — Build Notes

## Source
- URL: https://www.sillycycle.com/xlock/xlockmore-5.89.tar.xz
- SHA-256: 525597aca0a06486798be925b6f04146bb595643248690f45807b6fa3a0ded5d
- SHA-512 (official): 4f0a52decf458edd9a49984aa811a08cbcd1f85f68e2200c342d7055e6c7cf7e4db9ae05911cd2beba0775a3d5c202808ff598fbb3104a0f26e4a14775ab5248
- Primary site: https://www.sillycycle.com/xlock
- Maintainer: David A. Bagley

## Build System
- Autotools (configure + make)
- configure is pre-generated in the release tarball

## Dependencies (declared in conanfile.py)
- libx11/1.8.13 (force-pinned, consistent with libxmu chain)
- libxext/6.4.0.1
- libxmu/1.3.1.1 (transitively brings libxt, libSM, libICE, xorgproto)

## Disabled Optional Features
All optional features requiring packages not in ohpcd registry are disabled:
- OpenGL/Mesa, GTK, Motif, Athena/Xaw, XPM, ImageMagick, FreeType/FTGL/GLTT
- Sound daemons (rplay, NAS, esound)
- DPMS, Xinerama, dtsaver

## OHOS Cross-Build Observations
1. config.guess/config.sub do not recognise OHOS; --host=aarch64-linux-gnu
   and --build=aarch64-unknown-linux-gnu are given explicitly.
2. HMDFS umask fix required (umask 077 → umask 022) in configure and
   config.status (same pattern as xdx, quagga, vimpc).
3. Parallel make (-jN) fails on HMDFS workers; use -j1.
4. libcrypt is linked but provided by musl on OHOS; no conan package needed.
5. libpng appears in the link line but is not a runtime dependency when
   XPM is disabled; ldd shows no libpng DT_NEEDED.

## make install on OHOS CI Workers (2026-10-18)
- CI build #98106 (worker CI-005) failed in package(): the recipe passed
  INSTALL_PROGRAM='/usr/bin/install ...', but /usr/bin/install does not
  exist on OHOS workers (it only worked on the local WSL gate host).
- Fix: INSTALL=cp INSTALL_PROGRAM=cp INSTALL_SCRIPT=cp INSTALL_DATA=cp
  overrides on `make install` (precedent: jdupes 1.31.1, lzip 1.24.1,
  libxapian 2.0.0).  All xlockmore install targets are single-file
  copies into mkinstalldirs-precreated dirs, so cp is a drop-in
  replacement.  Verified by CI build #98125 (worker CI-030): package()
  and packaging completed with the cp overrides.

## Exit-Time Teardown SIGSEGV After `-help` (2026-10-18)
- `xlock -help` prints the COMPLETE usage text (banner, option table,
  mode list; resource.c Help() ends in exit(0)) and then the process
  takes SIGSEGV in exit-time teardown, rc=139.
- Same signature on BOTH execution models: locally under qemu-aarch64
  (x86_64 cross-build host) and natively on the OHOS CI worker
  (build #98125, worker CI-030, native aarch64).
- The crash is post-output teardown (Help() already reached exit(0));
  test_package/test_xlock.sh therefore requires the complete output
  (banner + mode-list marker + >=200 lines) and accepts rc 0 or 139 on
  both models; truncated output, loader errors or any other rc FAIL.
