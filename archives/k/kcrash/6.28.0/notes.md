# kcrash 6.28.0 notes

## Scope

KDE Frameworks 6 `kcrash` for HarmonyOS PC (aarch64), first adaptation of
upstream `6.28.0`. It ships `libKF6Crash.so` — crash-handler support for KDE
applications (crash signal handling, DrKonqi launch, per-application crash
metadata, emergency save, auto-restart).

Base: the upstream `kcrash-6.28.0` release tarball, re-using the OHOS
adaptation set proven on `kcrash/6.26.0.1`.

## Relationship to 6.26.0.1

The 6.28.0 port changes three things relative to the 6.26.0.1 recipe; the
rest is carried over unchanged.

1. `patches/0001-CMakeLists.txt.patch` lowers the upstream `KF_DEP_VERSION`
   gate (used by `find_package(KF6CoreAddons 6.28.0)`) to the registry
   ceiling: kcoreaddons 6.28.0 is not published to the ohpcd registry (max
   6.26.0.1), while the kcrash 6.28.0 sources use no KF6CoreAddons API newer
   than 6.26 (kcontacts 6.28.0 precedent). The patch touches only the
   top-of-file version constant.
2. `tool_requires` moves to `extra-cmake-modules/6.29.0` to satisfy the
   upstream `find_package(ECM 6.28.0 NO_MODULE)` floor (the legacy `ecm`
   package used by 6.26.0.1 stops at 6.26.0).
3. `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` (OHOS only): the 6.28.0 device
   verification hit the HMDFS symlink wall at link time (see below), so the
   recipe now keeps the `-Wl,-soname,` flags and disables the versioned
   symlink chain (knowledge E330).

## Source

- URL: `https://mirrors.nju.edu.cn/kde/stable/frameworks/6.28/kcrash-6.28.0.tar.xz`
  — `download.kde.org` is unreachable from the sandbox/CI-worker network;
  mirrors.nju.edu.cn is an authoritative KDE mirror carrying the same
  tarball (same practice as the 6.26 line).
- SHA256 `ddcc14c0c40e24f4c0dc04246b87d11b650e6fd8be2cb00e4f2cc2ee9e605702`
  verified locally; two independent fetches of the mirror tarball are
  byte-identical. The extracted tree was cross-checked against the patch
  base (patch 0001 applies cleanly and the result matches the intended
  content byte-exactly).

## Adaptations (inherited from 6.26.0.1 unless marked NEW)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` — OHOS is not in KDE's platform allowlist.
- `BUILD_TESTING=ON` — the upstream CTest autotests run inside `build()`
  (`ctest --output-on-failure --no-tests=error` with `QT_QPA_PLATFORM=offscreen`
  and a scratch HOME/XDG tree so tests cannot touch the device config).
- `WITH_X11=OFF` — upstream defaults it ON for the UNIX branch HarmonyOS
  matches, but OHOS has no X11 headers/libs.
- `BUILD_DESIGNERPLUGIN=OFF` — Qt6UiPlugin is not published to ohpcd.
- SONAME handling: OHOS CMake ships no `Platform/HarmonyOS` module, so the
  `CMAKE_SHARED_LIBRARY_SONAME_*` flags are provided explicitly; **NEW**
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` suppresses the versioned SO
  symlink chain. The 6.28.0 verify run failed to link with
  `CMake Error: failed to create symbolic link '../bin/libKF6Crash.so.6':
  Permission denied` / `cmake_symlink_library: System Error: Permission
  denied` — the HMDFS user volume rejects `symlink(2)`. With the flag the
  build emits a single unversioned real `.so` that still carries the
  relocatable bare `DT_SONAME` (E330 no-versioned-soname-keep-soname-flag;
  ki18n 6.28.0 / kitemodels 6.28.0 precedent). ELF evidence on the packaged
  artifact: `DT_SONAME = libKF6Crash.so`; consumer `DT_NEEDED` entries are
  bare sonames (`libKF6CoreAddons.so.6`), no Conan cache absolute paths.
- All of the above variables are set through `toolchain.variables` (written
  into `conan_toolchain.cmake`). `cache_variables` alone would be silently
  dropped on this toolchain, which configures with an explicit
  `-DCMAKE_TOOLCHAIN_FILE` instead of the generated CMake preset (kpeople
  6.28.0 field lesson).
- `ECM_MODULE_PATH` is set manually because the CMakeDeps-shaped
  `ECMConfig.cmake` does not propagate the variable the project relies on.
- `conan_cmakedeps_paths.cmake` is created manually because qtbase uses
  `cmake_find_mode=none`, which prevents CMakeDeps from adding its
  `lib/cmake` builddir to `CMAKE_PREFIX_PATH`.
- ECM `KDEInstallDirs6` runs the qtbase `qtpaths` host tool during
  configure; the sandbox `LD_LIBRARY_PATH` contains an incompatible
  `libc++_shared.so` that shadows the working one, so `/system/lib64` is
  prepended for configure/build/test (kconfig 6.26.0 / bluez-qt 6.28.0
  precedent).

## test_package

The consumer builds `test_kcrash` (5 cases) and `consumer_crasher` (a real
crashing child process driven through `QProcess` with forwarded channels):

- `api-drkonqi-toggle`, `api-crash-handler-surface`,
  `api-error-information-setters` — public API surface (DrKonqi enable
  toggle, crash-handler accessors, `KCrash::setErrorMessage` /
  `setErrorInformation`).
- `e2e-emergency-save-on-crash` — a child process injects a crash and the
  emergency-save path fires.
- `e2e-autorestart-directly` — the child re-execs with
  `KCRASH_AUTO_RESTARTED` semantics after a crash.

`CMakeLists.txt` also registers the executable with CTest, so the R28
suite runs both ways (direct run and `ctest`).

## Verification

OHOS `conan create` verification passed on 2026-10-17 (HarmonyOS PC
device), `ohc-run.py conan-verify kcrash 6.28.0`, profile
`ci/conan/profiles/ohos-aarch64`, reference `kcrash/6.28.0@ohpcd/stable`:

| Step | Result |
|---|---|
| G0 预构建风险评估 | PASS (E092 known-risk handled in recipe) |
| G1 配方完整性 | PASS |
| G2 conan create (clean build) | PASS |
| G3 系统同名库隔离 | PASS |
| G4 产物完整性 | PASS |
| L2/L4/L5 | skipped (library package, no cache path) |

- Upstream CTest: **3/3 passed, 0 failed** —
  `kcrashtest` 2.92s (includes the crash-injection cases),
  `coreconfigtest` 0.04s, `metadatatest` 0.04s.
- `test_package`: ctest **1/1** (`test_kcrash` 1.57s) plus direct run
  **TEST SUMMARY: 5 passed, 0 failed**.
- Package: `kcrash/6.28.0@ohpcd/stable`, package id
  `0ac31baf2280e058baca76c037388fe82e2b86fb`, package revision
  `b2b806e335899ea375b1bc3dc607a9d9`.
- Report: `reports/conan-verify-report.md` (the raw `conan-create.log` is
  deliberately not archived).

**编译结束**: 2026-10-17
**最终状态**: built
