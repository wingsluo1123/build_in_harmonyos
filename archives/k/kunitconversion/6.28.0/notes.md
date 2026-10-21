# kunitconversion 6.28.0 notes

## Scope

This package adds the first HarmonyOS PC recipe for KDE Frameworks 6.28.0
kunitconversion (new package; the repository has no earlier kunitconversion
entry). The only prior OHOS work is the j669539 kunitconversion5 5.116.0
port, PR !14840, which serves as the adaptation precedent. KUnitConversion
is the KDE Frameworks 6 unit-conversion library
(`libKF6UnitConversion.so`): the Converter / Value / Unit / UnitCategory API
over the compiled unit tables (Length, Area, Volume, Temperature, Velocity,
Mass, Pressure, Energy, Currency, Power, Time, FuelEfficiency, Density,
WeightPerArea, Acceleration, Angle, Frequency, Force, ThermalConductivity,
ThermalFlux, ThermalGeneration, Voltage, ElectricalCurrent,
ElectricalResistance, Permeability, BinaryData) plus the downloadable ECB
exchange-rate table.

Upstream tarball: `kunitconversion-6.28.0.tar.xz`, sha256
`b3e7dc0ad758a994f5171c6fb9a4bbf59bb51bdf7e0fecf0df6a3b55f2e5bd6b`
(https://download.kde.org/stable/frameworks/6.28/kunitconversion-6.28.0.tar.xz).
The conandata.yml keeps the official URL first and adds the NJU KDE mirror
as a fallback for workers whose regional Mirrorbits target (bfsu) has a
broken certificate chain; sha256 is the official value.

## Upstream test surface

`autotests/` registers 4 CTest entries carrying 17 QTest functions:
valuetest (6), categorytest (5), convertertest (5), currencytableinittest
(1). Two of them, `convertertest::testCurrency()` and
`categorytest::testCurrencyTableUpdate()`, exercise the ECB currency-table
download over HTTPS; the remaining functions only touch the compiled
tables. `currencytableinittest` copies an embedded `currency.xml` snapshot
into the QStandardPaths test-mode data dir
(`$HOME/.qttest/share/libkunitconversion/`) and parses it fully offline.

## Patches

`patches/0001-CMakeLists.txt.patch` (1 hunk, patch_ng pre-checked), top-level
CMakeLists.txt: `set(KF_DEP_VERSION "6.28.0")` -> `"6.26.0"` (`# ohpcd KF6
dep ceiling`). The published KF6 packages top out at 6.26.0.1 / 6.26.0
(ki18n); KF6 keeps API/ABI compatibility inside the 6.x major.

`patches/0002-src-CMakeLists.txt.patch` (1 hunk, patch_ng pre-checked), in
src/CMakeLists.txt: drops the `KF6::I18n` imported target from the
KF6UnitConversion link list, keeps its include directories via
`$<TARGET_PROPERTY:KF6::I18n,INTERFACE_INCLUDE_DIRECTORIES>`, adds
`$<TARGET_LINKER_FILE_DIR:KF6::I18n>` to the link directories and links the
library by bare name (`-lKF6I18n`) - ki18n 6.26.0 publishes
`libKF6I18n.so` without `DT_SONAME`, so an imported-target link records the
absolute conan-cache path in `DT_NEEDED` (platform entry E537); only the
PRIVATE link section changes, the exported interface is untouched.

`patches/0003-ohos-skip-currency-network-autotests.patch` (2 hunks): adds a
`QSKIP("currency-table network download needs an outbound HTTPS route,
unavailable on OHOS")` guard as the first statement of
`convertertest::testCurrency()` and `categorytest::testCurrencyTableUpdate()`.
These two are the only upstream test sources touched; the verification
logic stays in the tree and no test registration changes. The offline
currency paths remain fully covered (`valuetest::testCurrencyNotDownloaded`,
`currencytableinittest`). Precedent: j669539 kunitconversion5 5.116.0
(!14840); knowledge entry E731 (QSKIP network boundary guard). No platform
conditional-compilation macro is used anywhere in the patches.

## OHOS adaptation points (problem / root cause / solution)

1. **KF6 dependency ceiling.** The project runs
   `find_package(KF6I18n ${KF_DEP_VERSION} REQUIRED)` with
   `KF_DEP_VERSION=6.28.0`, which the published ki18n ConfigVersion file
   (6.26.0) rejects. Patch 0001 lowers the floor to 6.26.0 and the recipe
   pins `ki18n/6.26.0` (the highest registered version).

2. **ki18n_install(po) without a patch.** The top-level `ki18n_install(po)`
   routes through `KI18N_INSTALL()` in the ki18n package's
   KF6I18nMacros.cmake; with `KF_SKIP_PO_PROCESSING=ON` it early-returns,
   so no msgfmt / Qt6 LinguistTools is needed at configure time. The
   published ki18n/6.26.0 already ships the relaxed Gettext lookup (its own
   patch 0001), so the po layer needs no patch here (ki18n 6.28.0
   precedent).

3. **ECM tool_requires and module path.** `find_package(ECM 6.28.0
   NO_MODULE)` is satisfied by the `extra-cmake-modules/6.28.0`
   tool_requires (the legacy `ecm` package stops at 6.26.0).
   `ECM_MODULE_PATH` is exported directly because the project's
   `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})` relies on it
   (kcontacts 6.28.0 precedent).

4. **CMakeDeps paths.** qtbase, the KF6 packages and this package use
   `cmake_find_mode=none`, so CMakeDeps does not emit
   `conan_cmakedeps_paths.cmake`; the recipe writes it manually with all
   dependency lib/cmake dirs and the ECM module path (kcontacts 6.28.0
   precedent).

5. **C++20.** The CMakeDeps toolchain defaults to C++17; current KF6 code
   requires C++20, so `CMAKE_CXX_STANDARD=20` plus `-std=c++20` in
   `CMAKE_CXX_FLAGS` (kcontacts 6.28.0 precedent).

6. **Python bindings off.** The upstream guard
   (ANDROID OR APPLE OR WIN32 OR HAIKU OR NOT BUILD_SHARED_LIBS) does not
   cover OHOS and the bindings would require Shiboken6/PySide6, which are
   not published: `BUILD_PYTHON_BINDINGS=OFF`.

7. **E330: SONAME + HMDFS symlink denial.** CMake has no
   Platform/HarmonyOS module (the OHOS profile maps os=OHOS to
   CMAKE_SYSTEM_NAME=HarmonyOS), so
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` stays empty and the library
   would link without DT_SONAME. Worse, the target sets VERSION/SOVERSION
   (upstream SOVERSION 6), whose `.so.6`/`.so.6.28.0` symlink chain cannot
   be created on the HMDFS user volume (`symlink()` -> EPERM), failing the
   post-link `cmake_symlink_library` step. Fix: restore the soname flags
   and set `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` (both `variables` and
   `cache_variables` channels) so the build emits one unversioned real
   `libKF6UnitConversion.so` carrying a bare, relocatable DT_SONAME
   (DRAFT-cmake-harmonyos-system-name-soname; kpeople / kcontacts 6.28.0
   precedents).

8. **E537: ki18n's soname-less library would put an absolute cache path
   into DT_NEEDED.** For an imported target CMake puts the imported
   location path on the link line, and the linker records a soname-less
   library verbatim - forbidden for published artifacts (platform entry
   E537). Fix (patch 0002): drop the `KF6::I18n` target, keep its include
   directories explicitly, and link by bare name - the linker records the
   bare basename. Post-hoc binary rewriting (patchelf) is not viable on
   the HMDFS user volume, which rejects `mmap(PROT_EXEC)` on rewritten
   files (kcontacts 6.28.0 precedent).

9. **Test runtime environment.** HOME/XDG_CACHE_HOME/XDG_CONFIG_HOME/
   XDG_DATA_HOME/XDG_RUNTIME_DIR redirected below the build folder,
   `QT_QPA_PLATFORM=offscreen`, `CTEST_OUTPUT_ON_FAILURE=1`,
   `CTEST_PARALLEL_LEVEL=1`, `/system/lib64` (plus the SDK llvm/lib)
   prepended to LD_LIBRARY_PATH. The QStandardPaths test-mode data dir
   (`$HOME/.qttest/share/libkunitconversion/`) is pre-created because
   currencytableinittest copies its embedded snapshot there and
   `QFile::copy` does not create parent directories (j669539
   kunitconversion5 !14840 precedent). The ctest runtime also materializes
   the `bin/` + `../bin` sibling layouts with a symlink-then-copy fallback
   (HMDFS EPERM -> `shutil.copy2`; qzxing precedent).

10. **E731: QSKIP network boundary.** The two ECB-download functions
    cannot run in the OHOS CI sandbox (no outbound HTTPS route); patch
    0003 skips them in place while the entry-level CTest result stays
    `100% tests passed, 0 tests failed out of 4` (a QSKIP inside a QTest
    still exits 0). The skip reason is printed verbatim by ctest -V.

## Verification

Device conan-verify run (2026-10-17, ohos-aarch64 profile, clang 15,
Conan 2.29.1): G0 / G1 / G2 / G3 / G4 PASS; L2 / L4 / L5 skipped ("no cache
path reported" - the verify tool's standard outcome for this library-only
layout). Verdict: PASS (2026-10-17T01:27:49.841588).

- Upstream CTest inside conan create: `100% tests passed, 0 tests failed
  out of 4`. QSKIP lines captured with ctest -V:
  `SKIP : ConverterTest::testCurrency() currency-table network download
  needs an outbound HTTPS route, unavailable on OHOS` (convertertest:
  6 passed, 0 failed, 1 skipped) and the CategoryTest sibling
  (categorytest: 6 passed, 0 failed, 1 skipped).
- test_package: `test_kunitconversion` `TEST SUMMARY: 17 passed, 0 failed`;
  `test_kunitconversion_ohos` `TEST SUMMARY: 6 passed, 0 failed`; CTest 2/2.
- Artifact: `libKF6UnitConversion.so`, md5
  `1f6285ed9fc7a24ccd7737ee4fe140dc`, `DT_SONAME libKF6UnitConversion.so`
  (bare), no RUNPATH/RPATH. `DT_NEEDED` - 5 entries, all bare basenames,
  none containing `/`: `libQt6Network.so.6`, `libKF6I18n.so`,
  `libQt6Core.so.6`, `libc++_shared.so`, `libc.so`. E537 + E330 resolved
  and additionally asserted at consumer level by `test_kunitconversion_ohos`
  on every `conan create`.
- Reports: `reports/conan-verify-report.md` (md5
  `339b7f93905b80433aaf6068dde0971e`, 1257 bytes) ships with the archive;
  `reports/conan-create.log` (md5
  `1e4b7506f5d3007b706315a6d4922e1b`, 12296 bytes) was retrieved from the
  device and md5-verified on both ends.

Two earlier device cycles hardened the recipe before the green run: cycle 1
exposed that conandata.yml patches keyed by anything but the version string
make `apply_conandata_patches` silently apply zero patches (the rejected
`find_package(KF6I18n 6.28.0)` was the only symptom); cycle 2 exposed that
upstream `src/velocity.cpp` stores the km/h factor as `0.277778` (six
significant digits), so 1 m/s round-trips to 3.5999971 and the consumer
check needs a precision-tolerant comparison (1e-4), not exact equality.

- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
