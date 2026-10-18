# kcontacts 6.28.0 notes

## Scope

This package refreshes the published `kcontacts/6.18.0` HarmonyOS PC recipe to
KDE Frameworks 6.28.0. KContacts is the address book library behind the Akonadi
KF baseline: the Addressee / ContactGroup / Address data models, the vCard
2.1/3.0/4.0 and LDIF parsers/serializers, the AddressFormatter (postal address
rendering, KI18nLocaleData-backed country metadata) and the vCard MIME
drag/drop helper. The 6.18.0 recipe served as the starting point.

Upstream tarball: `kcontacts-6.28.0.tar.xz`,
sha256 `389d6128f18bee9113844615f535eeb870605f6fce968ca5c18d85a22478b8a2`
(https://download.kde.org/stable/frameworks/6.28/kcontacts-6.28.0.tar.xz).
The conandata.yml keeps the official URL first and adds the NJU KDE mirror as
a fallback for workers whose regional Mirrorbits target (bfsu) has a broken
certificate chain; sha256 is the official value.

## Upstream changes 6.18.0 -> 6.28.0 (relevant to the OHOS adaptation)

- `cmake_minimum_required` 3.29 and Qt minimum 6.9.0: satisfied by the device
  CMake 4.1.2 and qtbase/6.11.1.
- `find_package(ECM 6.28.0 NO_MODULE)`: needs the extra-cmake-modules/6.28.0
  tool_requires (the legacy `ecm` package stops at 6.26.0).
- `find_package(KF6 ${KF_DEP_VERSION} REQUIRED COMPONENTS CoreAddons I18n
  Config Codecs)` with `KF_DEP_VERSION=6.28.0`; lowered to the published ohpcd
  ceiling 6.26.0 by patches/0001 hunk 1.
- `include(ECMQmlModule)` stays unconditional (patch hunk 2 wraps it in
  `if(USE_QML)`); QML stays off.
- `ki18n_install(po)` unchanged at the top level (patch hunk 3 comments it
  out).
- `ecm_setup_version(... SOVERSION 6)` plus
  `set_target_properties(KF6Contacts PROPERTIES VERSION ${KCONTACTS_VERSION}
  SOVERSION ${KCONTACTS_SOVERSION})` in src/CMakeLists.txt: the shared library
  would be built under versioned names - see adaptation point 4.
- autotests: 32 registered CTest entries (29 ecm_add_tests unit tests,
  kcontacts-testroundtrip, kcontacts-addressformattest, kcontacts-picturetest);
  `vcardtool_benchmark` is compiled but not registered. The `tests/` sample
  programs (testread/testwrite/testread2) are built alongside.

## Patches

`patches/0001-CMakeLists.txt.patch` (3 hunks, patch_ng pre-checked), all in
the top-level CMakeLists.txt:

1. `set(KF_DEP_VERSION "6.28.0")` -> `"6.26.0"` (`# ohpcd KF6 dep ceiling`).
   The published KF6 packages top out at 6.26.0.1 (Config/CoreAddons/Codecs)
   and 6.26.0 (I18n); KF6 keeps API/ABI compatibility inside the 6.x major.
2. `include(ECMQmlModule)` wrapped in `if(USE_QML)` (with USE_QML=OFF):
   ECMQmlModule runs an unconditional non-QUIET
   `find_package(Qt6 COMPONENTS Core Qml)`, and Qt6Qml is not part of the
   published qtbase package. This also skips the QML plugin subdirectory.
   (DRAFT-ecm-qmlmodule-noquiet-required-trap)
3. `ki18n_install(po)` commented out (`# disabled: requires Qt6
   LinguistTools, not published to ohpcd`): it routes through
   `ecm_install_po_files_as_qm` -> `find_package(Qt6 LinguistTools REQUIRED)`.
   Translations only; no effect on the library or its ABI.

`patches/0002-src-CMakeLists.txt.patch` (1 hunk, patch_ng pre-checked), in
src/CMakeLists.txt: drops the `KF6::I18n` / `KF6::I18nLocaleData` imported
targets from the KF6Contacts link list and links both libraries by bare name
while keeping their include directories (adaptation point 10).

No upstream test source or test registration is modified.

## OHOS adaptation points (problem / root cause / solution)

1. **KF6 dependency ceiling.** `find_package(KF6 6.28.0 ...)` is rejected by
   the published KF6 ConfigVersion files (6.26.0.x). Patch hunk 1 lowers the
   floor to 6.26.0; the recipe pins kconfig/kcoreaddons/kcodecs 6.26.0.1 and
   ki18n 6.26.0.

2. **Qt6Qml not published.** USE_QML=OFF plus patch hunk 2; the QML plugin and
   the `if(BUILD_TESTING)` `find_package(Qt6 Quick)` block resolve as OPTIONAL.

3. **Qt6 LinguistTools not published.** `ki18n_install(po)` is disabled by
   patch hunk 3.

4. **SONAME + HMDFS symlink denial.** CMake has no Platform/HarmonyOS module
   (the OHOS profile maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS), so
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` stays empty and the library
   would link without DT_SONAME. Worse, with `VERSION`/`SOVERSION` set CMake
   appends a versioned `libKF6Contacts.so.6`(.28.0) symlink chain after
   linking, and the HMDFS user volume rejects `symlink()` with EPERM/EACCES -
   the post-link `cmake_symlink_library` step fails the build
   (`failed to create symbolic link '../bin/libKF6Contacts.so.6': Permission
   denied`, observed in the first device run at 21% of the build).
   Fix: restore the soname flags and set
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` (both `variables` and
   `cache_variables` channels), so the build emits one unversioned real
   `libKF6Contacts.so` carrying `DT_SONAME libKF6Contacts.so` - no symlink
   step at build or install time, and the library's own DT_SONAME stays bare
   and relocatable (two soname-less KF6 dependencies originally wrote
   absolute DT_NEEDED paths into the artifact - see point 10 for the fix).
   (DRAFT-cmake-harmonyos-system-name-soname; kpeople 6.28.0 and
   kcolorpicker 0.3.1 precedents; the expat #1912 hit is the first HMDFS
   symlink-denial record.)

5. **iso-codes unlock for the country-backed address tests.** KI18nLocaleData
   (KCountry) locates `iso-codes/json/*.json` through QStandardPaths /
   XDG_DATA_DIRS. OHOS ships no `/usr/share/iso-codes`, which is why 6.18.0
   excluded `kcontacts-addresstest` and `kcontacts-addressformattest`
   (30/30 with 2 excluded). This recipe takes `iso-codes/4.16.0` as a runtime
   requirement and prepends every dependency's `share/` tree to
   XDG_DATA_DIRS for the test run, so both tests execute
   (device-verified layout: `share/iso-codes/json/iso_3166-1.json` etc.).

6. **MIME database for vcarddragtest.** OHOS ships no freedesktop
   shared-mime-info database; the recipe stages a minimal database
   (`text/directory` alias `text/x-vcard`, `text/plain` glob `*.txt`) with
   `update-mime-database` from the shared-mime-info/2.5.1 tool_requires and
   prepends it to XDG_DATA_DIRS (kcontacts 6.18.0 precedent).

7. **Test runtime environment.** HOME/XDG_CACHE_HOME/XDG_CONFIG_HOME/
   XDG_DATA_HOME/XDG_RUNTIME_DIR redirected below the build folder,
   QT_QPA_PLATFORM=offscreen, `CTEST_OUTPUT_ON_FAILURE=1`,
   `CTEST_PARALLEL_LEVEL=1`, `/system/lib64` (plus the SDK llvm/lib) prepended
   to LD_LIBRARY_PATH to shadow the sandbox libc++ (kcalendarcore 6.26.0
   precedents).

8. **ctest runtime links.** Some KDE binaries resolve siblings through a
   `../bin` relative layout when the install rpath is stripped; the recipe
   materializes `<build>/../bin/libKF6Contacts.so` next to the build folder
   with a symlink-then-copy fallback (HMDFS EPERM -> `shutil.copy2`;
   qzxing precedent). With the restored soname the loader resolves through
   LD_LIBRARY_PATH as well.

9. **CMakeDeps paths.** qtbase and the KF6 packages use
   `cmake_find_mode=none`, so CMakeDeps does not emit
   `conan_cmakedeps_paths.cmake`; the recipe writes it manually with all
   dependency lib/cmake dirs and the ECM module path (kfilemetadata 6.28.0
   precedent). `ECM_MODULE_PATH` is also exported directly because the
   project's `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})` relies on it.

10. **E537: ki18n's soname-less libraries put absolute cache paths into
    DT_NEEDED.** Device `readelf -d` showed two of the nine DT_NEEDED
    entries recording absolute conan-cache paths
    (`.../p/ki18n9378b4d80136f/p/lib/libKF6I18n.so` and the LocaleData
    sibling) - forbidden for published artifacts (platform knowledge entry
    E537). Root cause: ki18n 6.26.0 publishes `libKF6I18n.so` and
    `libKF6I18nLocaleData.so` without `DT_SONAME` (the `.1` soname-fix
    republishes cover kconfig / kcoreaddons / kcodecs, not ki18n); for an
    imported target CMake puts the imported location path on the link line,
    and the linker records a soname-less library verbatim. A first attempt
    that stamped `IMPORTED_SONAME` / cleared `IMPORTED_NO_SONAME` on the
    imported targets proved ineffective on device (CMake 4.1.2 kept the
    absolute path on the link line; the artifact was byte-identical). Fix
    (patches/0002): drop the two targets from the KF6Contacts link list,
    keep their include directories explicitly, and link both libraries by
    bare name (`-L<package lib dir> -lKF6I18n -lKF6I18nLocaleData`) - the
    linker then records bare basenames. The `-l`-records-the-basename
    behavior was confirmed on the device linker with a minimal probe before
    the full rebuild. Keeping DT_NEEDED bare at link time is E537's
    prescribed method: post-hoc binary rewriting (patchelf) is not viable
    on the HMDFS user volume, which rejects `mmap(PROT_EXEC)` on rewritten
    files.

11. **Consumer SONAME/DT_NEEDED regression test.** The E537 fix (point 10)
    and the bare-SONAME decision (point 4) are properties of the shipped
    binary that a later edit could silently revert - a re-added KF6::I18n
    target or a lost soname flag would produce a binary that only fails to
    load on machines without the build cache, while `conan create` still
    reports green. `test_package/test_ohos_soname.cpp` (target
    `test_kcontacts_ohos`, registered with CTest and run directly from
    `test()`) parses ELF64 little-endian dynamic sections itself: six
    checks assert that (a) the KContacts API round-trips in the consumer
    process, (b) the consumer executable's DT_NEEDED entries are all bare
    basenames, (c) the consumer references `libKF6Contacts.so` by its bare
    SONAME, and then re-opens the produced `libKF6Contacts.so` - primarily
    through the LD_LIBRARY_PATH candidate list the loader itself used, with
    the `/proc/self/maps` pathname as a fallback - and asserts (d) it
    opens and parses, (e) its DT_SONAME is the bare basename and (f) all of
    its DT_NEEDED entries (nine observed) are bare. The maps pathname is
    deliberately only a fallback: it is the kernel-side canonical view of
    the conan cache (e.g. `/data/service/el2/100/hmdfs/account/files/
    Docs/.conan2/...`), which the test process cannot open even though the
    loader mapped it. No platform macros are used, so the check runs
    wherever the package is built.

## Verification

Device conan-verify run (2026-10-16, ohos-aarch64 profile, clang 15,
Conan 2.29.1): G0 / G1 / G2 / G3 / G4 PASS; L2 / L4 / L5 skipped ("no cache
path reported" - the verify tool's standard outcome for this library-only
layout). Verdict: PASS.

- Upstream CTest: 100% tests passed, 0 tests failed out of 32 (run inside
  conan create, runtime env = iso-codes share/ via XDG_DATA_DIRS, staged
  vCard MIME database, QT_QPA_PLATFORM=offscreen).
- test_package: `test_kcontacts` 7 passed, 0 failed and
  `test_kcontacts_ohos` 6 passed, 0 failed (both TEST SUMMARY lines);
  CTest 2/2 (both entries registered via add_test).
- Artifact: `libKF6Contacts.so`, md5 `70b7ffa5b530c6bfda09ad58ee691259`,
  `DT_SONAME libKF6Contacts.so` (bare), no RUNPATH/RPATH.
- `DT_NEEDED` - 9 entries, all bare basenames, none containing `/`:
  `libQt6Gui.so.6`, `libKF6CoreAddons.so.6`, `libKF6ConfigCore.so.6`,
  `libKF6Codecs.so.6`, `libKF6I18n.so`, `libKF6I18nLocaleData.so`,
  `libQt6Core.so.6`, `libc++_shared.so`, `libc.so`. E537 resolved: the
  previous revision recorded absolute ki18n cache paths for the two I18n
  entries; artifact md5 changed from `f5c491a0...` to `70b7ffa5...`.
  The same properties are asserted at consumer level on every
  `conan create` by `test_kcontacts_ohos` (point 11): both its
  consumer-executable checks and its re-opened-artifact checks pass.
- Reports: `reports/conan-create.log` (md5
  `03f6b9006989fb58c820c5d67ab20e97`, 65939 bytes),
  `reports/conan-verify-report.md` (md5
  `7abc8c6212f7ecd2c1981f1d9d8c12b8`, 1239 bytes), pulled from the device
  and md5-verified on both ends.

- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
