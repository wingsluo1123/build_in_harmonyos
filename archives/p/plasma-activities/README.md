# Plasma Activities

plasma-activities is the KDE Plasma activities library. It exposes the
activities model used by Plasma workspaces and applications:
`KActivities::Consumer` (read the activity list and the current activity),
`KActivities::Controller` (add/remove activities, rename, switch),
`KActivities::Info` (per-activity metadata), plus the
`org.kde.activities` QML module and the `plasma-activities-cli6`
diagnostic tool. It is the base of the Plasma 6 stack used by this
repository (libplasma -> kscreenlocker -> kwin).

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- The Qt provider is `qtbase-sql-dbus/6.11.1`. The plain `qtbase` package
  in this repository is built with `FEATURE_dbus=OFF` and has no Sql
  module, while plasma-activities needs Qt6 Core+DBus at the top level and
  Gui/Qml/Quick/Sql for the QML module. `qtbase-sql-dbus` is the superset
  build that provides all of them; it is prepended last in both the
  `CMAKE_PREFIX_PATH` and the runtime `LD_LIBRARY_PATH` (kactivitymanagerd
  6.7.2 precedent).
- `qtdeclarative/6.11.1` provides Qt6 Qml/Quick for the QML module;
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` points at its prefix so
  `find_package(Qt6 COMPONENTS Qml Quick)` resolves.
- Shared libraries are emitted unversioned with an explicit bare SONAME
  (`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` plus `-Wl,-soname,` flags): the
  HMDFS user volume on the device rejects `symlink()` with EPERM, so CMake
  cannot create the upstream `libPlasmaActivities.so.7` chain.
- `/system/lib64` and the OHOS SDK `llvm/lib` are prepended to
  `LD_LIBRARY_PATH` during configure/build/test; the sandbox default
  contains an incompatible `libc++_shared.so`, and ECM's KDEInstallDirs
  runs the qtbase `qtpaths` host tool at configure time.
- Upstream registers only `QFlatSetTest` with CTest. The
  `PlasmaActivitiesTest` integration runner is built but not registered,
  and needs a running `kactivitymanagerd` over a session D-Bus, which the
  OHOS sandbox does not provide.

## Dependencies

- Compile/runtime: qtbase-sql-dbus (Qt6 Core/DBus/Gui/Widgets/Sql),
  qtbase (for qtdeclarative/kconfig/kcoreaddons), qtdeclarative (Qml/Quick),
  kconfig, kcoreaddons
- Build: ecm (extra-cmake-modules), CMake, ninja/make

## Verification

The `test_package` builds a real consumer executable against the installed
`PlasmaActivities` CMake package and drives the offline contract
(service status, default activity list, Controller futures, Info
availability, unknown-id handling) as 7 independently judged cases, ending in
`TEST SUMMARY: N passed, M failed`; any failure exits 1.

## References

- Upstream: <https://invent.kde.org/plasma/plasma-activities>
- Source: <https://download.kde.org/stable/plasma/6.7.2/plasma-activities-6.7.2.tar.xz>
