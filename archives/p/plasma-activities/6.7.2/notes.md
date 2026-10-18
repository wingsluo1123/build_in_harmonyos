# plasma-activities 6.7.2 notes

## Scope

This package is part of the KDE Plasma 6.7.2 train (task: plasma-activities,
【依赖项】). It provides the activities library at the base of the Plasma 6
stack used by this repository (libplasma -> kscreenlocker -> kwin) and was
already required in source form by the archived kactivitymanagerd 6.7.2
build; this archive makes it a first-class ohpcd package.

Ships:

- `libPlasmaActivities.so` - Consumer / Controller / Info C++ API plus its
  D-Bus client.
- `org.kde.activities` QML module (`plasmaactivitiesextensionplugin`).
- `bin/plasma-activities-cli6` - diagnostic CLI.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- Qt provider is `qtbase-sql-dbus/6.11.1`: the top-level CMakeLists asks for
  `Qt6 Core` + `Qt6 DBus` and `src/imports/CMakeLists.txt` asks for
  `Gui/Qml/Quick/Sql`. The plain `qtbase/6.11.1` package is built with
  `FEATURE_dbus=OFF` and ships neither Qt6DBus nor Qt6Sql, while
  `qtbase-sql-dbus` is the superset build that supplies Core/DBus/Gui/
  Widgets/Sql/Test from one coherent build (kactivitymanagerd 6.7.2
  precedent). Plain `qtbase/6.11.1` stays in the graph because
  qtdeclarative/kconfig/kcoreaddons were built against it; both
  `CMAKE_PREFIX_PATH` and `LD_LIBRARY_PATH` get the qtbase-sql-dbus prefix
  prepended last so it wins every lookup.
- `qtdeclarative/6.11.1` supplies Qt6 Qml/Quick for the QML module;
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` points at its prefix because
  Qt6Config.cmake resolves components relative to Qt6_DIR (analitza 26.04.0
  precedent).
- KF6 6.26 baseline: `kconfig/6.26.0.1` + `kcoreaddons/6.26.0.1`, the two
  frameworks linked by `src/imports/CMakeLists.txt` (KF6::ConfigCore,
  KF6::CoreAddons).
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` plus explicit `-Wl,-soname,` flags
  (both the `variables` and `cache_variables` channel): HMDFS on the device
  user volume rejects `symlink()` with EPERM, so the upstream
  `libPlasmaActivities.so.7 -> .so.7.0.0` chain cannot be created. The
  library is emitted under its plain name with a real `DT_SONAME` (E330
  family; kwidgetsaddons/analitza precedent).
- `ECM_MODULE_PATH` is set manually because the CMakeDeps-generated
  `ECMConfig.cmake` does not propagate the variable the KDE modules rely on.
- `conan_cmakedeps_paths.cmake` is written manually because every Qt/KF
  package here uses `cmake_find_mode=none`; the toolchain then finds their
  `lib/cmake` directories.
- `/system/lib64` and the OHOS SDK `llvm/lib` are prepended to
  `LD_LIBRARY_PATH` during configure/build/test: the sandbox
  `LD_LIBRARY_PATH` contains an incompatible `libc++_shared.so` under
  `/data/storage/el1/bundle/libs/arm64`, and ECM's KDEInstallDirs runs the
  qtbase `qtpaths` host tool during configure.
- `BUILD_TESTING=ON`. Only `QFlatSetTest` is registered with CTest upstream;
  see the inventory below.
- `patches/0001-manager-guard-null-session-bus.patch` (applied on every
  platform): when no session bus is reachable,
  `QDBusConnection::sessionBus().interface()` returns `nullptr`.
  `Manager::self()` and `Manager::serviceOwnerChanged()` dereference it
  unconditionally, so the first `Consumer` construction segfaults on OHOS
  (which has no session D-Bus) and on any headless system without one. The
  patch adds the missing null checks; it contains no platform macros, so it
  is unconditional (kscreenlocker 6.7.2 precedent).

## Upstream test inventory (rule4 evidence)

`autotests/core/CMakeLists.txt` builds two targets:

- `QFlatSetTest` (qflatset.cpp) - `add_test(NAME QFlatSetTest COMMAND
  QFlatSetTest)`; run by ctest here.
- `PlasmaActivitiesTest` (main.cpp custom TestRunner) - **no `add_test`**.
  Its sources define, outside QTest's own lifecycle slots:
  `OfflineTest::testOfflineActivityListing`,
  `OfflineTest::testOfflineActivityControl`,
  `CleanOnlineTest::testCleanOnlineActivityListing`,
  `CleanOnlineTest::testCleanOnlineActivityControl`,
  `OnlineTest::testOnlineActivityListing`,
  `Modifier::testProcess` - six further test functions plus
  `QFlatSetTest::test1`, seven in total.
  The runner spawns `kactivitymanagerd` via
  `QStandardPaths::findExecutable` and drives it over the session D-Bus.
  Neither the daemon nor a session bus exists in the OHOS sandbox, so this
  runner is built but not executed (upstream itself never runs it in CI
  through CTest either).

## Offline consumer contract

Without kactivitymanagerd the public API degrades in documented ways, which
the test_package drives as its E2E cases:

- `Consumer::serviceStatus()` returns `NotRunning`.
- `Consumer::activities()` returns exactly the null activity
  `00000000-0000-0000-0000-000000000000`; `currentActivity()` equals it.
- `Controller` setters/add/remove return already-finished futures:
  `addActivity()` yields an empty id, `setCurrentActivity()` yields false,
  `setActivityName()` completes as a void future.
- `Info` reports `Nothing` availability with empty name/description/icon and
  `activities://<id>` as URI; an unknown id keeps its id and URI, reports
  `Nothing` and is not current.
- The remaining `Controller` operations (`setActivityDescription`,
  `setActivityIcon`, `removeActivity`, `previousActivity`, `nextActivity`)
  also return already-finished void futures offline.
- `plasma-activities-cli6` is deliberately not used as the E2E executor: its
  `main()` busy-waits for `serviceStatus() == Running` and never terminates
  offline.

## Verification

- Source SHA256 verified against the official KDE `.sha256` file:
  `18379349eb05382a165d3b59c13b756fdb7e681b11d57ca9e2fbae3ffee4a34a`.
- One portability patch (null session-bus guard in `manager_p.cpp`), applied
  on every platform (pure null guard, no platform macros); the rest of the
  6.7.2 tarball is unmodified.
- OHOS `conan create` verification (device, 2026-10-18, clean rebuild after
  `conan remove 'plasma-activities/6.7.2@ohpcd/stable' -c`):
  `ohc-run.py conan-verify plasma-activities 6.7.2` -> Verdict PASS
  (G0/G1/G2/G3/G4 PASS; L2/L4/L5 skipped on device). The portability patch
  is applied during the build ("Apply patch (portability): ..."); upstream
  CTest runs `QFlatSetTest` 1/1 Passed (`100% tests passed, 0 tests failed
  out of 1`); test_package runs `consumer_e2e` 7/7 Passed, ending in
  `TEST SUMMARY: 7 passed, 0 failed`. RC=0.
- Product artifacts verified on device: `lib/libPlasmaActivities.so` with
  `SONAME=libPlasmaActivities.so` and bare-name `DT_NEEDED`
  (libQt6DBus.so.6 / libQt6Core.so.6), `lib/qml/org/kde/activities/`
  module files, `lib/cmake/PlasmaActivities`, `include/PlasmaActivities`,
  `bin/plasma-activities-cli6`.
- test_package: 7 offline consumer cases, each printing TEST PASS/TEST FAIL,
  ending in `TEST SUMMARY: N passed, M failed`; any failure exits 1.
