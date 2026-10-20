# kcompletion 6.28.0 notes

## Scope

KF6 6.28 train version bump of the existing `kcompletion` recipe (6.26.0.1
baseline). Path A (basic adaptation), archive dir
`archives/k/kcompletion/6.28.0`. No R37 version bump: neither the official
main nor the ohpcd registry had a kcompletion/6.28.0 entry before this change.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips po/qm catalog generation without a source
  patch: ECM's `ecm_process_po_files_as_qm()` returns early when the option is
  set, so no Qt6LinguistTools discovery happens (not published to ohpcd).
- `BUILD_DESIGNERPLUGIN=OFF`: the Designer plugin would need Qt6UiPlugin,
  which is not published to ohpcd.
- `patches/0001-CMakeLists.txt.patch` lowers `KF_DEP_VERSION` 6.28.0 ->
  6.26.0, the common floor of the published KF6 stack: ohpcd has kconfig and
  kcodecs up to 6.26.0.1 while kwidgetsaddons is at 6.28.0 (kbookmarks
  6.28.0 precedent). Single hunk.
- `BUILD_TESTING=ON` enables the upstream suite during the OHOS Conan package
  build: five CTest executables from `autotests/` (kcompletioncoretest,
  klineedit_unittest, kcombobox_unittest, kemailvalidatortest,
  ksortablelisttest).
- The three interactive demo programs in `tests/` (kcomboboxtest,
  kcompletionuitest, klineedittest) call `QApplication::exec()` and never
  return on their own. They are excluded from ctest with
  `-E "^(kcomboboxtest|kcompletionuitest|klineedittest)$"` (a ctest timeout
  would be a failure) and instead run as launch-alive smoke checks: offscreen
  under a 15 s timeout, still running = PASS, an early non-zero exit fails
  the build (kglobalaccel 6.28.0 precedent).
- `conandata.yml` gives the source URL as an R39 list: official
  download.kde.org URL first, then three authoritative mirrors (FTP.funet.fi,
  mirror.freedif.org, mirrorservice.org). download.kde.org 302-redirects to
  mirrors.bfsu.edu.cn from CN networks, which fails TLS certificate
  verification; conan's `get()`/`download()` natively treat a URL list as
  primary + mirrors on download error. The tarball is 2256440 bytes with
  sha256 `8aa9cbc3…be7cc3c`.
- The recipe is shared-only: `validate()` raises
  `ConanInvalidConfiguration` for `shared=False`, because the
  unversioned-soname workaround and `package_info()` describe
  `libKF6Completion.so`; a static package id would otherwise be paired with a
  shared library.
- Shared libraries are emitted unversioned through
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` plus explicit `-Wl,-soname,` flags
  (plain + cache variables): HMDFS rejects `symlink()` with EPERM, so CMake's
  versioned `.so` chain cannot be created on device; the ELF still carries a
  real DT_SONAME so consumers record bare sonames (kwidgetsaddons 6.28.0 /
  kbookmarks 6.28.0 precedent).
- Dependencies: `qtbase/6.11.1`, `kcodecs/6.26.0.1`, `kconfig/6.26.0.1`,
  `kwidgetsaddons/6.28.0`, build tool `ecm/6.28.0` (6.28.0 raises the ECM
  minimum to 6.28.0).
- ECM_MODULE_PATH is set manually because the CMakeDeps-generated
  ECMConfig.cmake does not propagate the variable the project relies on;
  `conan_cmakedeps_paths.cmake` is written by `generate()` because qtbase and
  the three KF6 packages use `cmake_find_mode=none`, which prevents CMakeDeps
  from adding their `lib/cmake` builddirs to `CMAKE_PREFIX_PATH`.

## Upstream delta 6.26.0 -> 6.28.0

- Top-level `CMakeLists.txt`: `KF_VERSION` and `KF_DEP_VERSION` 6.28.0;
  `find_package(ECM 6.28.0)`; deprecation floor raised KF 6.23 -> 6.27.
- `poqm/`: five translation files updated (ia, nb, nn, se, ug). `src/`,
  `autotests/` and `tests/` are byte-identical to 6.26.0.

## Verification

- OHOS `conan create` on the device: PASS. The final re-verification after
  the R3 fix (`test_package/conanfile.py` only) reused the cached package —
  the recipe revision is unchanged because `test_package/` is not exported
  into the recipe — and rebuilt/ran the consumer test only (29/29). The
  upstream CTest 5/5 and GUI smoke 3/3 evidence comes from the full build at
  the same recipe revision (verified on d97c848207, report 13:58:38).
- `conan-verify` gates, as recorded in `reports/conan-verify-report.md`:
  G0-G3 PASS; G4 PASS with a package-id lookup warning (`无法找到程序包 ID`;
  the runner had no cache path); L2/L4/L5 were **skipped** by the runner
  because no cache path was available. The report keeps the tool's fixed
  `✅ PASS` section headers for those gates while the bodies record
  `⏭️ 跳过（无 cache 路径）`; per the kew 4.2.5 / klick 0.12.2 precedent
  those headers are a reporting artifact and must not be read as runtime
  evidence — the authoritative gate statuses are listed under `local_ci:` in
  `manifest.yaml`. The `reports/conan-create.log` referenced by the report is
  a device-side raw log and is not shipped with the archive per platform
  policy.
- Upstream CTest 5/5 passed: kcompletioncoretest (15 passed), klineedit_unittest
  (9 passed), kcombobox_unittest (11 passed), kemailvalidatortest (7 data
  rows), ksortablelisttest (plain main, exit 0). rule4 count: 27 QTest
  functions across four files (kcompletioncore 13, klineedit 5, kcombobox 8,
  kemailvalidator 1) plus the ksortablelisttest script-type target.
- Interactive GUI smoke 3/3: kcomboboxtest, kcompletionuitest and
  klineedittest each reached the offscreen event loop and were still running
  when the 15 s timeout fired, so the build's launch-alive gate passed.
- Consumer `test_package` 29/29 checks in six cases: KCompletion prefix
  matching/cycling, sorted + case-insensitive lookup, weighted items()
  round-trip, KLineEdit inline completion, KComboBox editable completion and
  KEmailValidator states (offscreen).
- Consumer test note: the first draft called `makeCompletion()` on KLineEdit
  and KComboBox, which is protected and failed to compile. The shipped test
  uses the public `KLineEdit::doCompletion()` and, for the combo box,
  `qobject_cast<KLineEdit *>(combo.lineEdit())` before calling
  `doCompletion()`.
