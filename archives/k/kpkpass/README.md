# KPkPass

KPkPass is the KDE PIM Apple Wallet pass library. It provides
`KPkPass::Pass` and the boarding-pass/coupon/event-ticket/store-card
subclasses for reading `.pkpass` bundles (a ZIP containing `pass.json`,
localized `pass.strings` and image assets), plus the `org.kde.pkpass` QML
module exposing the pass types to QML. It is consumed by KDE itinerary
(`find_package(KPim6PkPass 6.6.0 CONFIG REQUIRED)`).

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allow-list
  (OHOS/HarmonyOS is not in the upstream list).
- `KF_SKIP_PO_PROCESSING=ON`: Qt6LinguistTools is not part of the qtbase
  package in this repository.
- The QML module `org.kde.pkpass` is built unconditionally upstream, so
  qtdeclarative is a hard dependency; qtbase/qtdeclarative use
  `cmake_find_mode=none` and are located through a hand-written
  `conan_cmakedeps_paths.cmake` (kitemodels 6.26.0 precedent).
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; `/system/lib64` is prepended to `LD_LIBRARY_PATH` so
  `qtpaths` resolves the compatible `libc++_shared.so` (kconfig 6.26.0
  precedent).
- `SharedMimeInfo` is found through ECM's find module, which runs
  `update-mime-database -v`; the recipe pins the shared-mime-info/2.5.1
  binary. Version 2.5.1 keeps both upstream MIME XML install rules off.
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` plus explicit `-Wl,-soname,`
  flags keep `DT_SONAME` on a single unversioned `libKPim6PkPass.so`
  (HMDFS refuses the versioned symlink chain; attica 6.14.0 precedent),
  and every packaged ELF is re-signed after CMake rewrites the install
  RUNPATH (kitemodels 6.26.0 precedent).
- Both upstream autotests (`pkpasstest`, `fieldtest`) run unmodified with
  `BUILD_TESTING=ON`.

## Dependencies

- Build: ecm (extra-cmake-modules) >= 6.13, shared-mime-info >= 1.8 (only
  for version detection), CMake >= 3.16, C++20
- Runtime/compile: qtbase (Qt6Core, Qt6Gui), qtdeclarative (Qt6Qml),
  karchive (KF6Archive)

## References

- Homepage: https://invent.kde.org/pim/kpkpass
- Apple Wallet pass format:
  https://developer.apple.com/library/archive/documentation/UserExperience/Conceptual/PassKit_PG/
