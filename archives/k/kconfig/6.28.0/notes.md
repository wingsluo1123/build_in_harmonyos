# kconfig 6.28.0 notes

## Scope

This package refreshes the published 6.26.0.1 HarmonyOS PC recipe to KDE
Frameworks 6.28.0. The 6.26.0.1 recipe was used as the starting point (base
recipe). The functional delta is the QML enablement: 6.28.0 builds and
ships the upstream `org.kde.config` QML module (`KCONFIG_USE_QML=ON`, the
upstream default) because `qtdeclarative` and `qtshadertools` are published
in the repository, and the upstream poqm translation step runs again now
that `qt6linguisttools/6.11.1` is available. This serves the
Plasma/KWin-style QML consumers that need the `KAuthorized` singleton.

## Upstream changes 6.26.0.1 -> 6.28.0 (relevant to the OHOS adaptation)

- Upstream 6.28.0 requires ECM >= 6.28.0 (`find_package(ECM 6.28.0 ...
  REQUIRED)`); the published `extra-cmake-modules/6.29.0` tool package is
  used as the build tool.
- `KCONFIG_USE_QML` defaults to ON upstream, so the `org.kde.config` QML
  module and the QML registration autotests are part of the normal build
  again; the 6.26 patch hunks that guarded them are obsolete by
  construction.
- The poqm step (`ecm_install_po_files_as_qm`) builds the translations
  with `Qt6LinguistTools`, now published as `qt6linguisttools/6.11.1`, so
  the 6.26 patch hunk that disabled poqm is dropped.
- `kconfigtest.cpp` still uses C++20 chrono calendar types
  (`days`/`weeks`/`months`/`years`), which remain unavailable with clang 15
  / libc++ / cppstd=17 on OHOS, so the test target is still skipped at
  build time.
- With the QML test set built again, the executed upstream autotest count
  grows from 68 (6.26.0.1) to 84; the same five OHOS exclusions apply via
  the ctest `-E` regex.

## Patch applicability (6.26.0.1 patch vs 6.28.0 source)

The OHOS delta is much smaller than in 6.26.0.1: the poqm-disabling hunk
and the QML guard hunks are no longer needed. The regenerated
`0001-CMakeLists.txt.patch` touches only `autotests/CMakeLists.txt`:

1. `kconfigtest.cpp` is moved out of `ecm_add_tests(...)` into an
   `if(NOT HARMONYOS)`-guarded `ecm_add_test`, because the OHOS toolchain
   cannot compile the C++20 chrono calendar types used by that test.
2. The matching `set_tests_properties(kconfigcore-kconfigtest ...)` call is
   guarded the same way.

`HARMONYOS` is the plain variable injected by the recipe toolchain
(`tc.variables["HARMONYOS"] = "1"` when `settings.os == "OHOS"`; CMake's
`CMAKE_SYSTEM_NAME` on this target is `HarmonyOS` but it does not define an
`HARMONYOS` variable by itself).

## Adaptations (inherited from 6.26.0.1)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KCONFIG_USE_QML=ON` (upstream default) builds and ships the
  `org.kde.config` QML module; `CMAKE_INSTALL_QMLDIR=lib/qml` pins the
  module tree next to the libraries (ksvg precedent).
- The upstream poqm step now runs with `qt6linguisttools/6.11.1`
  (previously patched out).
- `USE_DBUS=OFF` disables KConfig DBus integration.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during the Conan
  build.
- The OHOS runner excludes `kconfigcore-kconfigtest`,
  `kconfigcore-kdesktopfiletest`, `kconfigcore-test_kconf_update`,
  `kconfiggui-kstandardshortcutwatchertest`, and
  `kconfigcompiler-basic-test` (5 names, unchanged since 6.18.0);
  `kconfigcore-kconfigtest` is additionally skipped at build time.
- `DT_SONAME` is restored via `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` /
  `_C_FLAG` (OHOS CMake has no `Platform/HarmonyOS` module); without it the
  libraries and the QML plugin record build-tree relative paths in
  `DT_NEEDED`.
- `_cmake_build_env()` and the test environment prepend `/system/lib64` so
  the qtbase `qtpaths` host tool and the test executables resolve the
  compatible `libc++_shared.so`.

## Adaptation issues hit during this port (6.28.0-specific)

1. **Device symlinks under `/storage` are denied device-wide.** The
   versioned shared-library chain CMake creates by default
   (`libKF6ConfigCore.so -> libKF6ConfigCore.so.6 -> ...6.28.0`) fails to
   link with `cmake_symlink_library: Permission denied` (knowledge E540;
   the sibling kpeople 6.28.0 verify run hits the identical wall). Device
   builds therefore run with the device-local `ohos-aarch64-full` profile
   (`-pr:h/-pr:b ~/.conan2/profiles/ohos-aarch64-full`), whose
   `user_toolchain` (`no-versioned-soname.cmake`) strips
   `VERSION`/`SOVERSION` from every target at end of directory processing,
   yielding single unversioned `.so` files. Nothing about this ships in
   the recipe; the recipe itself is profile-agnostic.
2. **`KSharedConfig::openConfig("name_rc")->name()` returns the identifier
   as passed (relative).** The raw-file persistence check in the consumer
   test resolved the file against the current working directory instead of
   `XDG_CONFIG_HOME`; it now builds the absolute path through
   `QStandardPaths::writableLocation(GenericConfigLocation)`.
3. **The `org.kde.config` QML plugin can load asynchronously.** The
   `QQmlComponent` stayed in the `Loading` state with an empty
   `errorString()`, and `create()` failed with "Component is not ready".
   The QML consumer case now waits (bounded, 30 s) on `statusChanged` and
   checks `isReady()` before instantiating.
4. **The test suite runs twice per create (ctest round plus direct
   execution) against one `XDG_CONFIG_HOME`.** The second round read the
   first round's rc files ("defaults are count=99 label=written"), making
   the default-value checks non-deterministic; both test executables now
   remove their rc files at process start.
5. **Do not remove a Conan cache package folder with `rm -rf`.** The stale
   package listing makes the next `conan create` crash with
   `os.utime ... FileNotFoundError` (rc 7) right after "Already
   installed!". `conan remove "kconfig/6.28.0" -c` is the clean path.

## Verification

- Upstream source SHA256 verified against the official
  `kconfig-6.28.0.tar.xz.sha256` and cross-checked against a second
  independent mirror:
  `24e26e516b7904a26661eab7d2064bee1ac57165571e85b4da6020fd36f14322`.
- OHOS `conan create` verification passed on 2026-10-16 (HarmonyOS PC
  device).
- Command: `conan create . -pr:h ~/.conan2/profiles/ohos-aarch64-full
  -pr:b ~/.conan2/profiles/ohos-aarch64-full --build=missing
  -c tools.build:jobs=3`
- Package reference: `kconfig/6.28.0` (recipe revision
  `752cbbab736a4106835821d753913c8a`, package id
  `1b9180db9e62194d8376b684eec9400c9e837e9c`; settings armv8/Release,
  clang 15, cppstd 17, libc++, os=OHOS 6.0, shared=True).
- Upstream CTest: **84/84 executed tests passed, 0 failed**
  (`100% tests passed, 0 tests failed out of 84`), executed with
  `BUILD_TESTING=ON` inside `conan create`. The run is invoked with the
  exclusion regex `ctest -E
  "^(kconfigcore-kconfigtest|kconfigcore-kdesktopfiletest|kconfigcore-test_kconf_update|kconfiggui-kstandardshortcutwatchertest|kconfigcompiler-basic-test)$"`,
  and `kconfigcore-kconfigtest` is additionally skipped at build time
  (C++20 chrono calendar types unavailable with clang 15 / libc++ /
  cppstd=17).
- Conan `test_package`: ctest 2/2 OK; `test_kconfig` **6/6 passed, 0
  failed** (config-group-roundtrip, shared-config-persistence,
  skeleton-typed-roundtrip, cli-tools-kwriteconfig-kreadconfig,
  window-config-save-restore, qml-org-kde-config-kauthorized);
  `test_kconfig_xt` **3/3 passed, 0 failed** (xt-defaults, xt-save,
  xt-reload).
- Package artifacts: `bin/kreadconfig6`, `bin/kwriteconfig6`,
  `bin/kf6/kconf_update`, `bin/kf6/kconfig_compiler_kf6`,
  `lib/libKF6ConfigCore.so`, `lib/libKF6ConfigGui.so`,
  `lib/libKF6ConfigQml.so`, `lib/qml/org/kde/config/` (qmldir, plugin,
  qmltypes, module version), `lib/cmake/KF6Config/` (7 files), `include/`.

---

**编译结束**: 2026-10-16 02:45
**最终状态**: built
