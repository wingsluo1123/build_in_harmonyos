# kpkpass 25.12.3 notes

## Scope

KDE PIM Apple Wallet pass library. The package publishes KPim6PkPass
(PIM_VERSION 6.6.3, SOVERSION 6) and the QML module `org.kde.pkpass`, and
satisfies itinerary's `find_package(KPim6PkPass 6.6.0 CONFIG REQUIRED)`.
There is no prior kpkpass recipe in this repository (version bump not
required) and no task card for it, so this is a dependency self-import.

## Upstream build requirements

- CMake >= 3.16, C++20 (`CMAKE_CXX_STANDARD 20` in the top-level file).
- Qt6 >= 6.8: Gui, Qml (Qml is needed by the always-built QML plugin in
  `src/quick`), and Qt6Test for the autotests.
- KF6 >= 6.13: Archive (KZip reads the `.pkpass` bundle).
- ECM >= 6.13.
- SharedMimeInfo >= 1.8 when not building for Android. The version only
  selects the MIME XML install rules: `< 2.2` installs
  `application-vnd-apple-pkpass.xml` and `< 2.5` installs
  `application-vnd-apple-pkpasses.xml`. With shared-mime-info 2.5.1 both
  rules are disabled automatically, so no MIME database update runs during
  install.

## OHOS adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allow-list
  (OHOS/HarmonyOS is not listed).
- `KF_SKIP_PO_PROCESSING=ON`: Qt6LinguistTools is not part of the qtbase
  package in this repository; the source tree has no `po/` directory.
- `BUILD_QCH=OFF` (default) so the optional Qt Help target is not built.
- The QML plugin is unconditional upstream. `qtdeclarative/6.11.1` is a
  hard requirement; qtbase and qtdeclarative both use
  `cmake_find_mode=none`, so their `lib/cmake` dirs are added to
  `CMAKE_PREFIX_PATH` through a hand-written `conan_cmakedeps_paths.cmake`.
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` carries both package folders so
  Qt's multi-package layout resolves.
- The same prefix file exposes `karchive/6.26.0`'s builddir, so
  `find_package(KF6 COMPONENTS Archive)` resolves through ECM's
  `FindKF6` module and `find_dependency(KF6Archive 6.13.0)` in the
  installed `KPim6PkPassConfig.cmake` finds the component config.
- ECM 6.26+ `KDEInstallDirs6` runs the qtbase `qtpaths` host tool at
  configure time; `/system/lib64` is prepended to `LD_LIBRARY_PATH` so the
  compatible `libc++_shared.so` is found instead of the sandbox one
  (kconfig 6.26.0 precedent).
- `find_package(SharedMimeInfo 1.8 REQUIRED)` is resolved by ECM's
  `FindSharedMimeInfo`, which runs `update-mime-database -v`. The recipe
  pins `UPDATE_MIME_DATABASE_EXECUTABLE` to the shared-mime-info/2.5.1
  package binary and runs configure with the build-context library dirs on
  `LD_LIBRARY_PATH` so the tool resolves glib/libxml2.
- OHOS CMake does not emit a SONAME for shared libraries by default; without
  it the QML plugin would record a build-tree path in DT_NEEDED. The recipe
  sets `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` plus explicit
  `-Wl,-soname,` flags: HMDFS refuses the versioned `.so.6`/`.so` symlink
  chain CMake would create, so the package carries a single unversioned
  `libKPim6PkPass.so` that still records `DT_SONAME` (attica 6.14.0
  precedent).
- CMake install rewrites the RUNPATH of installed shared libraries, which
  invalidates the OHOS build-time `.codesign` section; every packaged ELF
  (the library and the QML plugin) is stripped of the old signature and
  re-signed with `binary-sign-tool -selfSign 1`.

## C++ standard

The upstream top-level file sets `CMAKE_CXX_STANDARD 20` after `project()`,
and the recipe also sets the toolchain cache variable to 20 so no
`-std=gnu++17` from the ohos-aarch64 profile leaks into the compile line.
The sources themselves use no C++20-only library facilities (they use Qt 6
APIs such as `QStringDecoder`), so the value is mostly an upstream contract.

## Tests

Upstream autotests build two QTest binaries with `BUILD_TESTING=ON`:
`pkpasstest` and `fieldtest`. Each has one `testBoardingPass` slot besides
the `initTestCase` lifecycle slot, and both read
`autotests/data/boardingpass-v1.pkpass`. They run unmodified in the Conan
build (ctest manifest is checked to contain exactly 2 cases).

The test_package builds an installed C++ consumer against
`KPim6::PkPass`, parses an embedded copy of the same CC0 fixture through
`Pass::fromData`, checks fields/barcode/locations/logo/raw data, and
imports the installed `org.kde.pkpass` QML module with QQmlEngine.
