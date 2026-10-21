# ki18n 6.28.0 notes

## Scope

KDE Frameworks 6 `ki18n` for HarmonyOS PC (aarch64), first adaptation of
upstream `6.28.0`. It is the front dependency of `kirigami-app 1.0.1`: it
ships the **QML module `org.kde.ki18n`** (`lib/qml/org/kde/ki18n`) in addition
to the core libraries `libKF6I18n.so`, `libKF6I18nLocaleData.so` and
`libKF6I18nQml.so`.

Base: the upstream `ki18n-6.28.0` release tarball, carrying over the QML
module, SONAME and ELF-resign hardening proven on `ki18n/6.26.0.1` and
`kitemodels/6.18.0.1` (PR #10520) / `kirigami/6.26.0` (PR #10787).

## Relationship to 6.26.0.1

The 6.28.0 port re-uses the 6.26.0.1 recipe. Upstream moved the ECM floor to
6.28.0 (top-level `CMakeLists.txt`) and an `ecm/6.28.0` binary is published in
the registry (2026-10-14), so the only recipe change is the `tool_requires`
pin. The rest of the 6.26.0 → 6.28.0 source delta is small and Qt-6.11-era:
`FindLibIntl` accepts `gnuintl`, `ktranscript.cpp` uses `Q_APPLICATION_STATIC`
(Qt ≥ 6.10), and the i18n-qml headers include the lowercase
`qqmlintegration.h` — all satisfied by qtbase/qtdeclarative 6.11.1.
`cmake/KF6I18nMacros.cmake.in` is byte-identical between the two releases, so
patch 0001 applies unchanged.

The `org.kde.ki18n` QML module this recipe ships was introduced upstream in
KF **6.21** (`src/i18n-qml/CMakeLists.txt`: `ecm_add_qml_module(KF6I18nQml URI
"org.kde.ki18n" VERSION 1.0 GENERATE_PLUGIN_SOURCE)`); 6.18/6.19/6.20 only
build `libKF6I18nQml.so` with no QML module, which is why the 6.18 line cannot
produce it.

## Source

- URL: `https://download.kde.org/stable/frameworks/6.28/ki18n-6.28.0.tar.xz`
  (official KDE release; no re-pack / fork).
- SHA256 verified locally: `820ce5858c6db732d68da53572a0e7db8353e4372d2122debcfb0f9ff10b85db`.
- `conandata.yml` lists the official URL first with authoritative mirror
  fallbacks (`mirrors.nju.edu.cn`, `mirrors.aliyun.com`): on the direct-download
  path the official URL 302s to a Mirrorbits mirror that presented an invalid
  certificate (`SSLCertVerificationError`); the fallbacks carry the same
  official tarball and are sha256-pinned (R39/E299).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` — OHOS is not in KDE's platform allow-list.
- `BUILD_WITH_QML=ON` — qtdeclarative/6.11.1 (Qt6::Qml) is published and is a
  hard requirement, so `src/i18n-qml` and `src/localedata-qml` are configured,
  built and installed.
- `KF_SKIP_PO_PROCESSING=ON` — skips ki18n's own translation catalog build.
- `BUILD_TESTING=ON` — upstream CTest autotests run inside `build()` (R51).
- `CMAKE_INSTALL_LIBDIR=lib` so the QML tree lands in `lib/qml`.
- `ECM_MODULE_PATH` set manually (the CMakeDeps-generated ECMConfig.cmake does
  not propagate it).
- Qt split-package resolution: qtbase + qtdeclarative are prepended to
  `CMAKE_PREFIX_PATH`/`CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH` and to
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` through a hand-written
  `conan_cmakedeps_paths.cmake` (both ship relocatable Qt6*Config.cmake with
  `cmake_find_mode=none`).
- `_dependency_runtime_env()` puts the dependency `lib`/`bin`/`libexec` dirs on
  `LD_LIBRARY_PATH`/`PATH` during configure/build/install: the Qt host tools
  (`qmltyperegistrar`, `qmlcachegen`, `moc`, `rcc`) have a RUNPATH pointing only
  at their own package yet still load `libQt6Core.so.6` from qtbase.

### SONAME / DT_NEEDED hardening (kitemodels 6.18.0.1, attica 6.14.0)

OHOS CMake emits no SONAME by default. The QML plugin linked against the sibling
build-tree library then records `../../bin/libKF6I18n.so` in DT_NEEDED, which the
OHOS loader treats as a cwd-relative path and fails to resolve (this is exactly
the defect shipped by ki18n/6.18.0.1). `_configure_ohos_shared_library_rules()`
restores `CMAKE_SHARED_LIBRARY_SONAME_*` / `CMAKE_SHARED_LIBRARY_RUNTIME_*`
through `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX`; the plugin now records the bare
SONAME (`libKF6I18n.so`).

Upstream additionally sets `VERSION`/`SOVERSION`, so with the SONAME flags in
place CMake would create the versioned symlink chain
`libKF6I18n.so.6.28.0 -> libKF6I18n.so.6 -> libKF6I18n.so`
(`cmake_symlink_library`). The OHOS/HMDFS user volume rejects `symlink()` with
EPERM ("System Error: Permission denied"), which fails the link step. The recipe
therefore also sets `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` (keeping
`-Wl,-soname,` emission): CMake emits a single unversioned real `.so` carrying
the relocatable bare SONAME and performs no symlink calls (E330; the same
incantation as the merged attica/6.14.0 and attica5/5.116.0 recipes).

### ELF re-signing

CMake rewrites the RUNPATH of installed shared libraries, which invalidates the
OHOS build-time `.codesign` section (the loader then reports "Permission
denied"). `package()` walks the package tree and re-signs every ELF with
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign --selfSign 1`
(6 ELF files for this package).

### Gettext patch

`patches/0001-cmake-KF6I18nMacros.cmake.in.patch` changes
`find_package(Gettext REQUIRED)` to `find_package(Gettext QUIET)` in
`KF6I18nMacros.cmake.in`, so consumers that only link `KF6::I18n` are not forced
to locate the Gettext command-line tools. Platform-agnostic (R8), no platform
macros in the patch.

Note: the Conan-generated gettext CMake config declares a non-existent
`asprintf` library and shadows CMake's own `FindGettext` module; the
test_package therefore disables that config via
`CMakeDeps.set_property("gettext", "cmake_find_mode", "none")`.

### ktranscript test-config deploy patch (0002)

`patches/0002-autotests-testhelpers.patch` rewrites the config deployment in
`deployTestConfig()` (`autotests/testhelpers.cpp`, 1 hunk). The upstream helper
copies the test's `.ini` into the Qt test home with `QFile::copy()`; on the
OHOS user volume Qt 6.11 takes its engine-level copy path (`copy_file_range()`
class) and, when that fails with an unexpected error, reports failure without
falling back to a block copy - the deployment then fails deterministically
(observed identically on two CI workers: `Failed to copy test config file
.../ktranscript-test.ini`, with the destination directory present and the
source file readable). The patch replaces the copy with a plain `read()`/
`write()` block loop plus a permissions copy, so the ktranscript autotest runs
to completion on the target filesystem. Platform-agnostic (R8), no platform
macros; the upstream test logic itself is untouched.

## Verification

`conan create archives/k/ki18n/6.28.0 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
--build=missing --user=ohpcd --channel=stable` on a HarmonyOS PC device: PASS
(same profiles/flags as the platform CI; the run log is kept in the device
workspace, not in this archive).

- Upstream CTest: **12/12 executed passed** (`ctest -N`: 16 registered; the 4
  `KF6::I18nLocaleData` tests `kcatalogtest`/`kcountrytest`/
  `kcountrysubdivisiontest`/`ktimezonetest` are excluded — they require the
  optional IsoCodes JSON runtime data, not shipped on OHOS).
- Conan test_package: R34 C++ API + R53 `import org.kde.ki18n` through an
  offscreen `QQmlEngine`, plus qmldir/plugin/.qmltypes and DT_NEEDED assertions.
- conan-verify (G0 risk check / G1 recipe integrity / G2 conan create): PASS.

## Artifacts

```
lib/libKF6I18n.so                     (SONAME libKF6I18n.so)
lib/libKF6I18nLocaleData.so           (SONAME libKF6I18nLocaleData.so)
lib/libKF6I18nQml.so                  (SONAME libKF6I18nQml.so)
lib/plugins/kf6/ktranscript.so          (Qt6Qml translation script plugin)
lib/qml/org/kde/ki18n/qmldir            (module org.kde.ki18n)
lib/qml/org/kde/ki18n/libKF6I18nQmlplugin.so
lib/qml/org/kde/ki18n/KF6I18nQml.qmltypes
lib/qml/org/kde/i18n/localeData/{qmldir,libki18nlocaledataqmlplugin.so,*.qmltypes}
lib/cmake/KF6I18n/KF6I18nConfig.cmake (+ Targets/Macros/…)
include/KF6/KI18n/…, include/KF6/KI18nLocaleData/…
```

All shared libraries ship unversioned (`libKF6I18n.so` etc.) because of
`CMAKE_PLATFORM_NO_VERSIONED_SONAME` (E330) — no `.so.6`/`.so.6.28.0` symlink
chain exists.

No `bin/` directory → R38 `commands.json` is not applicable (pure library +
QML plugin).

## Knowledge gained

- `org.kde.ki18n` was introduced in KF 6.21; 6.18/6.19/6.20 cannot produce it.
- The QML type is the singleton `KI18n` (`LocalizedContext`, `QML_NAMED_ELEMENT`),
  not `KLocalizedContext`; `KLocalization::setupLocalizedContext()` must run
  before QML loads so the singleton can locate the engine root-context object.
- No-SONAME → relative DT_NEEDED; fix with `CMAKE_USER_MAKE_RULES_OVERRIDE`.
- HMDFS user volumes reject `symlink()`/`mkfifo` (EPERM): any upstream
  `VERSION`/`SOVERSION` makes CMake's `cmake_symlink_library` chain fail.
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `-Wl,-soname,` yields one
  unversioned real `.so` with a bare relocatable SONAME (E330).
- Post-install ELF edit invalidates `.codesign`; re-sign every packaged ELF.
- Conan gettext config shadows `FindGettext` on OHOS (`asprintf`); suppress it
  with `cmake_find_mode=none`.
---

**编译结束**: 2026-10-16 02:18
**最终状态**: built
