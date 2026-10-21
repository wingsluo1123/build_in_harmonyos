# KConfig

KConfig is the KDE Frameworks 6 configuration system. It provides
KConfig/KConfigGroup for INI-style persistent configuration,
KDesktopFile for freedesktop.org desktop entry files, KCoreConfigSkeleton /
KConfigSkeleton for typed settings classes, and the kconfig_compiler code
generator (KConfig XT) that turns `.kcfg` XML descriptions into C++ setting
classes. Since KF 6.21 it also ships the `org.kde.config` QML module
(KAuthorized singleton, WindowStateSaver, KConfigPropertyMap) used by
Plasma/KWin-style QML consumers.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `USE_DBUS=OFF` disables KConfig DBus integration.
- From 6.28.0, `KCONFIG_USE_QML=ON` (the upstream default) builds and ships
  the `org.kde.config` QML module at `lib/qml/org/kde/config` with
  `qtdeclarative/6.11.1`; `qtshadertools/6.11.1` is also required because
  Qt6Quick links Qt6::ShaderTools. `CMAKE_INSTALL_QMLDIR=lib/qml` pins the
  module tree next to the libraries.
- From 6.28.0, the upstream poqm translation step runs with
  `qt6linguisttools/6.11.1` (patched out in earlier revisions because Qt
  Linguist tools were not available); ECM >= 6.28.0 is required upstream,
  provided by `extra-cmake-modules/6.29.0`.
- `DT_SONAME` is restored via `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` /
  `_C_FLAG` (OHOS CMake has no `Platform/HarmonyOS` module); without it the
  libraries and the QML plugin record build-tree relative paths in
  `DT_NEEDED`.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- From 6.26.0 the upstream `kconfigtest` uses C++20 chrono calendar types
  which the OHOS toolchain (clang 15 / libc++ / cppstd=17) cannot compile;
  the patch skips building that test target on HarmonyOS (it was already on
  the run-time exclusion list).
- Known limitations: five upstream tests are excluded from the runner
  (`kconfigcore-kconfigtest`, `kconfigcore-kdesktopfiletest`,
  `kconfigcore-test_kconf_update`, `kconfiggui-kstandardshortcutwatchertest`,
  `kconfigcompiler-basic-test`).

## Shipped tools

- `bin/kreadconfig6`, `bin/kwriteconfig6` (hicmd 真机验证通过),
  `bin/kf6/kconf_update`
- `bin/kf6/kconfig_compiler_kf6` (KConfig XT generator; consumed through
  the installed `kconfig_add_kcfg_files` CMake function and the
  `KF6::kconfig_compiler` imported target)

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0+), ninja/make
- 6.28.0: qtbase (Qt6Core/Qt6Xml/Qt6Gui), qtdeclarative (Qt6Qml/Qt6Quick),
  qtshadertools (Qt6ShaderTools for Qt6Quick); build tools
  extra-cmake-modules/6.29.0 and qt6linguisttools/6.11.1
- 6.26.0.1 and older: qtbase only; ecm build tool

## References

- Homepage: https://invent.kde.org/frameworks/kconfig
- Sources: https://download.kde.org/stable/frameworks/
