# kconfigwidgets 6.20.0 notes

## Scope

First OHOS PC (aarch64) adaptation of KDE Frameworks `kconfigwidgets` 6.20.0.
The package is needed as a hard dependency of `koko` 26.04.0 (KF >= 6.20).
It is derived from the existing 6.18.0 package in this archive but targets the
6.26.0 KF baseline published in the OhPCD artifact repository.

## Upstream facts (from the 6.20.0 tarball, not guessed)

- `CMakeLists.txt:3-5`: `KF_VERSION` / `KF_DEP_VERSION` = `6.20.0`,
  `project(KConfigWidgets VERSION ${KF_VERSION})`.
- `CMakeLists.txt:8-9`: `find_package(ECM 6.20.0 NO_MODULE)` with
  `set_package_properties(... TYPE REQUIRED)`.
- `CMakeLists.txt:27-32`: `find_package(Qt6 6.8.0 CONFIG REQUIRED Widgets)`;
  additionally `find_package(Qt6GuiPrivate 6.8.0 REQUIRED)` **when Qt >= 6.10**.
  The OHOS baseline ships Qt 6.11.1, so `qtbase-gui` (Qt6GuiPrivate) is a hard
  requirement of this package, not an optional extra.
- `CMakeLists.txt:56-62`: KF6 deps at `${KF_DEP_VERSION}` (>= 6.20.0), all
  `REQUIRED`: CoreAddons, Codecs, Config, GuiAddons, I18n, WidgetsAddons,
  ColorScheme.
- `CMakeLists.txt:105`: `ecm_feature_summary(... FATAL_ON_MISSING_REQUIRED_PACKAGES)`.
- `CMakeLists.txt:36-44`: `USE_DBUS` defaults ON on UNIX; it pulls
  `Qt6 DBus` (REQUIRED) — kept OFF here, see below.
- `CMakeLists.txt:48`: `BUILD_DESIGNERPLUGIN` is a `cmake_dependent_option`
  that needs `Qt6UiPlugin`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist (OHOS is
  not a listed KDE platform).
- `USE_DBUS=OFF` because Qt6 DBus is not part of the published `qtbase`
  baseline; the D-Bus-backed KCMultiDialog hooks are dropped.
- `BUILD_DESIGNERPLUGIN=OFF` because `Qt6UiPlugin` is not published to OhPCD.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation in the
  cross-build package path.
- `BUILD_TESTING=ON` so the upstream CTest suites (`autotests/`, `tests/`) run
  inside `conan create`.
- KF6 siblings are pinned to the published 6.26.0 line (`kconfig`,
  `kcoreaddons`, `kguiaddons`, `ki18n`, `kwidgetsaddons`, `kcolorscheme`,
  `kcodecs/6.26.0.1`) because they satisfy upstream's `>= 6.20.0` and are the
  only 6.2x line actually published; `ecm/6.26.0` as `tool_requires`.
- `ECM_MODULE_PATH` is set manually: the CMakeDeps-generated `ECMConfig.cmake`
  does not export the variable that the project's CMakeLists relies on.
- `conan_cmakedeps_paths.cmake` is written manually because `qtbase` uses
  `cmake_find_mode=none`, so CMakeDeps cannot add its `lib/cmake` to
  `CMAKE_PREFIX_PATH`.

## Verification

- Source: `https://download.kde.org/stable/frameworks/6.20/kconfigwidgets-6.20.0.tar.xz`
  sha256 `5c5e8dc7e986d85c3602b8a52b8d8909f91e7433ecad8037099491250f5f4e36`
  (value taken from the official `.sha256` file next to the tarball and
  re-verified after download).
- W0: all ten requires probed with `conan download --only-recipe -r=ohpcd` →
  PUBLISHED (`ecm/6.26.0`, `qtbase/6.11.1`, `qtbase-gui/6.11.1`,
  `kconfig/6.26.0`, `kcoreaddons/6.26.0`, `kcodecs/6.26.0.1`,
  `kguiaddons/6.26.0`, `ki18n/6.26.0`, `kwidgetsaddons/6.26.0`,
  `kcolorscheme/6.26.0`).
- `conan create . -pr:a=ohos-aarch64 -r=ohpcd` → success.
  - Upstream CTest: **7/7 passed** (`kstandardactiontest`,
    `kconfigdialog_unittest`, `klanguagenametest`, `kcmdbartest`,
    `khamburgermenutest`, `krecentfilesaction_test`, `kopenaction_test`).
  - `test_package`: **1/1 passed**, real `KConfigDialog` consumer.
- No source patch is required for this version.
- Local build note: the KDE redirector pointed at `mirrors.bfsu.edu.cn`, which
  timed out from this machine; the identical tarball (same sha256) was seeded
  into the Conan sources cache from `mirrors.nju.edu.cn`. `conandata.yml` keeps
  the official `download.kde.org` URL.

## Test_package assertion corrected during adaptation

The first consumer test asserted that a second `addPage()` switches
`currentPage()`. That assumption is wrong: `KConfigDialog::addPage()` only
appends via `KPageDialog::addPage` (`src/kconfigdialog.cpp:118-198`), so the
current page stays the first one. The test now asserts the real semantics
(append does not switch) plus an explicit `setCurrentPage()` switch, which is
verified against the upstream source above.

## Package reference

`kconfigwidgets/6.20.0#4b6abd5d61da4cc103cbc4b737c9da6c:bee7b83d1f9c843bfdccaba2e27b396383fe3062#3eba53439dde9c2f963673ab416853e9`
---

**编译结束**: 2026-10-18 12:20
**最终状态**: built
