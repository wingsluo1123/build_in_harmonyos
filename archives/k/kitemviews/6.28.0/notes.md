# kitemviews 6.28.0 notes

## Scope

This package is part of the KF6 6.28 baseline (task #15355, dependency chain:
extra-cmake-modules 6.28.0 + qtbase 6.11.1). It updates the existing
HarmonyOS PC recipe from 6.26.0 to KDE Frameworks 6.28.0 (train delivery, no
version suffix). The 7-file shape mirrors the 6.26.0 line (conandata,
conanfile, one po/qm patch, test_package); the recipe adds the OHOS
shared-library-rules fix described below.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotest during the Conan build.
- `ecm_install_po_files_as_qm(poqm)` is disabled (patch 0001) because the Qt
  Linguist tools component is not part of the qtbase package used by this
  repository.
- ECM `KDEInstallDirs6` runs the qtbase `qtpaths` host tool during configure;
  `/system/lib64` and the qtbase lib dir are prepended to `LD_LIBRARY_PATH`
  so the compatible `libc++_shared.so` wins over the sandbox default
  (kconfig 6.26.0 precedent).
- OHOS shared-library rules are SONAME-only: the recipe writes a
  `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` rules file that defines only
  `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`/`_CXX_FLAG` (`-Wl,-soname,`) and sets
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`. Rationale: when the
  `CMAKE_SHARED_LIBRARY_RUNTIME_*` flags are defined, cmake's `install()`
  rewrites the ELF (strips the RUNPATH) and the OHOS loader refuses to
  dlopen the installed library (EACCES); with SONAME-only rules `install()`
  is a byte-identical copy of the build artifact.
- The consumer test (test_package) drives all three widget families; case 3
  (KCategorizedView) follows the canonical ordering required by
  KCategoryDrawer — see Verification.

## Verification

OHOS `conan create` verification passed on 2026-10-16 (fresh build in a new
cache folder; recipe revision exported 2026-10-15 19:27 UTC).

- Source SHA256 verified:
  `2b474a0a0ca1d59111ab864d4f05100e0056b5204d52dfbab6776ca0fbfdd402`.
- Full package reference:
  `kitemviews/6.28.0@ohpcd/stable#76472cea74156150fb6d56c39ed6ae91:57ffd8c720a5bfee7e8827990cd6550a49181c1b#1e243284dd12ed23384fdc583915c83e`.
- Upstream CTest: 1/1 passed (`kitemviews-klistwidgetsearchlinetest`,
  Passed 0.33 s; 100% tests passed, 0 tests failed out of 1). The 3 tests/
  GUI demos built but are not CTest-registered upstream; each was launched
  under offscreen QPA and stays in its event loop (timeout rc=124, no crash).
- Conan `test_package`: 27 checks / 3 consumer cases passed
  (TEST SUMMARY: 3 passed, 0 failed).
- Install == build artifact: md5 `812802935386db608fb349d1db885ace` on both
  sides; `readelf -d` shows SONAME only (no RPATH/RUNPATH); DT_NEEDED bare
  basenames.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir
  (library only).
- KCategoryDrawer crash note: sorting the category proxy before populating
  the source model leaves a phantom Block (QHash::operator[] default
  insertion) and `KCategoryDrawer::drawCategory` (kcategorydrawer.cpp:48)
  dereferences the invalid QModelIndex — deterministic SIGSEGV. The
  canonical order (setModel -> populate -> sort) plus waiting for both
  category blocks (lazy heights) passes 27/27. Upstream master carries the
  same code path.
