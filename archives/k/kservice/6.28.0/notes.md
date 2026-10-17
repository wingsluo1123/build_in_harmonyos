# kservice 6.28.0 notes

## Scope

This package carries the HarmonyOS PC adaptation of KDE Frameworks 6.28.0
kservice forward from 6.26.0. It keeps the 6.14.0/6.18.0/6.26.0 OHOS
adaptation set and adds the SONAME/independence fixes proven on the 6.28.0
line (ki18n 6.28.0 pattern), so the L5 soname gate that was recorded as a
non-blocking failure on 6.26.0 is addressed at the source instead of being
inherited.

## Upstream verification

- Upstream tag `v6.28.0` verified via
  `git ls-remote https://invent.kde.org/frameworks/kservice.git`:
  `refs/tags/v6.28.0` -> annotated tag object
  `e50b354ff603795da854d9ede58ef5dfd58eecf0`, peeled commit
  `4cb121c641370cfe49f6911400298f692d4ea65d`.
- Official tarball
  `https://download.kde.org/stable/frameworks/6.28/kservice-6.28.0.tar.xz`
  downloaded (mirror-resolved) and SHA-256 verified against the official
  `.sha256` companion file:
  `d9151195b748361a12d7aeafd8df531d2f45b55d202d7fa5f47c3a11d59877d6`.

## Upstream CMakeLists.txt dependency check (6.28.0)

- `cmake_minimum_required(VERSION 3.29)` (unchanged from 6.26.0; the CI
  toolchain satisfies this).
- `find_package(ECM 6.28.0 NO_MODULE)` — satisfied by `ecm/6.28.0`
  (tool_requires, published on ohpcd).
- `REQUIRED_QT_VERSION 6.9.0`, `find_package(Qt6 ... REQUIRED Xml)` —
  satisfied by `qtbase/6.11.1` (components Core/Xml unchanged).
- `KF_DEP_VERSION "6.28.0"`: `find_package(KF6Config/KF6CoreAddons/KF6I18n
  6.28.0 CONFIG REQUIRED)` — the published KF6 stack stops at 6.26.0 (with
  .1 fix releases for kconfig/kcoreaddons), so patch 0001 lowers
  `KF_DEP_VERSION` to `6.26.0`; the `find_package(ECM 6.28.0)` floor is
  left untouched.
- `ecm_set_disabled_deprecation_versions(QT 6.11.0 KF 6.27.0)` — allowlist
  only; no deprecation warnings hit the error boundary.
- `KF6DocTools` optional (disabled via
  `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`).
- `ecm_setup_version(... SOVERSION 6 PACKAGE_VERSION_FILE
  KF6ServiceConfigVersion.cmake)` — the installed version file lets
  consumers `find_package(KF6Service 6.28.0)`.

## Upstream changes 6.26.0 -> 6.28.0 (relevant to the OHOS adaptation)

- `KF_DEP_VERSION` raised to 6.28.0 (handled by patch 0001 on OHOS).
- Deprecation allowlist raised to `KF 6.27.0` (no behavioural impact).
- Upstream CTest registration unchanged: autotests/ still registers
  ksycocatest, ksycoca_xdgdirstest, ksycocathreadtest, kservicetest,
  kapplicationtradertest, kmimeassociationstest (6 entries),
  ksycocatest/kservicetest RUN_SERIAL.
- `kservicetest.cpp` gained `using namespace std::chrono_literals; using
  namespace Qt::StringLiterals;` above `QTEST_MAIN`, which moved the
  fixture-copy site; patch 0004 was regenerated against the 6.28.0 file and
  applies cleanly.
- The 6.18.0 OHOS FS-sensitive test guard still applies cleanly:
  `testNonReadableSycoca` and `extraFileInFutureShouldRebuildSycocaOnce`
  bodies are unchanged.

## Adaptations

Inherited (verified against the 6.28.0 source):

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for
  OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_PYTHON_BINDINGS=OFF` avoids Shiboken/PySide requirements.
- `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON` keeps optional docs out of
  the baseline package.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  build; ctest runs inside `build()` with an isolated HOME/XDG root, a
  generated test-only MIME database on `XDG_DATA_DIRS`, the staged XDG menu
  fixture, the fs-sensitive guards switched on via
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1`, and `--no-tests=error`.
- E132: the OHOS SDK `llvm/lib` directory is prepended to
  `LD_LIBRARY_PATH` for configure/build (lld depends on the SDK's
  libxml2.so.16).
- The sandbox's incompatible `libc++_shared.so` is shadowed by prepending
  `/system/lib64` for configure, the test run and the packaged-tool runs
  (kconfig 6.26.0 / kcrash 6.26.0 precedent).
- Absolute `DT_NEEDED` entries pointing into the conan cache are repaired
  in the build tree (symlink to the packaged copy or re-sign in place), and
  every packaged ELF is re-signed (`binary-sign-tool sign -selfSign 1` after
  stripping `.codesign`) because CMake rewrote its RUNPATH after the
  build-tree signing.
- `ECM_MODULE_PATH` is set manually (the CMakeDeps-generated ECM config
  does not propagate it), and a `conan_cmakedeps_paths.cmake` is written
  manually because `qtbase` uses `cmake_find_mode=none`.

New for 6.28.0:

- OHOS SONAME emit: `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` point at a
  generated `ohos-shared-library-rules.cmake` restoring
  `CMAKE_SHARED_LIBRARY_SONAME_*` / `CMAKE_SHARED_LIBRARY_RUNTIME_*`
  (OHOS ships no Platform/HarmonyOS module, so no `-soname`/`-rpath` flag
  would otherwise be emitted), and
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` suppresses the versioned
  symlink chain (`libKF6Service.so.6.28.0 -> .so.6 -> .so`) that the HMDFS
  user volume rejects with E330. The result is a single unversioned
  `libKF6Service.so` carrying the bare, relocatable `DT_SONAME`
  (ki18n 6.28.0 pattern; attica/attica5 precedent).
- Packaged ELF `DT_NEEDED` normalization (`_normalize_ohos_needed_names`,
  `package()`): the published `ki18n/6.26.0` ships `libKF6I18n.so` without a
  `DT_SONAME`, so linking records its absolute conan-cache path in
  `DT_NEEDED` — in the shipped `bin/kbuildsycoca6` that makes the artifact
  startable only on machines carrying a conan cache at that exact path
  (E537 family). Every packaged ELF (tool + library) is scanned; path-form
  `libKF6*`/`libQt6*` entries are rewritten in place to bare basenames with
  equal-length NUL padding (`.dynstr` offsets stay valid), and the tree is
  re-signed afterwards. Merged precedent: kiconthemes 6.18.0.1/6.26.0,
  kirigami 6.18.0, kjobwidgets 6.18.0, kirigami-addons 1.13.0, mauikit
  4.0.2.
- Patch 0001 lowers `KF_DEP_VERSION` 6.28.0 -> 6.26.0.

## Patches (applied only when `self.settings.os == "OHOS"`)

- `patches/0001-lower-kf-dep-version.patch` — `set(KF_DEP_VERSION
  "6.28.0")` -> `"6.26.0"` (portability; see above).
- `patches/0002-autotests-guard-ohos-fs-sensitive-checks.patch` — three
  ksycocatest subtests become env-gated skips behind
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS`, each skipped only when the
  runner's filesystem actually fails the upstream precondition: the two
  POSIX file-permission/timestamp-sensitive cases inherited from the
  merged 6.26.0 patch (`testNonReadableSycoca`,
  `extraFileInFutureShouldRebuildSycocaOnce`), plus
  `recursiveCheckShouldIgnoreLinksGoingUp`, whose `QFile::link("..")`
  symlink creation is rejected on the HMDFS user volume (E330 family; the
  2026-10-17 device run recorded `QFile::link(...)` returning FALSE). On
  symlink-capable runners that case still runs and asserts as upstream.
- `patches/0003-ohos-autotests-xdg-menu-fallback.patch` — inline fallback
  `applications.menu` when `QFINDTESTDATA("test-applications.menu")` cannot
  locate the fixture in the build tree (portability).
- `patches/0004-ohos-test-fixture-copy-fallback.patch` — `ohosCopyFixture`
  read()/write() block-copy fallback for the kservicetest desktop-file
  fixtures, whose `QFile::copy()` OS-level path fails on the OHOS user
  volume (portability).

Patch application verification: the four patches were applied sequentially
with `git apply` onto a pristine extraction of the official tarball and the
resulting tree is byte-identical to the reference scratch tree
(`TREE_IDENTICAL`), i.e. the 6.28.0 sources plus exactly these changes.

## Verification

Device `conan-verify` run, 2026-10-17, on the HarmonyOS PC device:

```
cd $HOME/bih && python3 scripts/ohc-run.py conan-verify kservice 6.28.0
```

- **Clean rebuild guaranteed**: before the run the package was removed with
  `conan remove "kservice/6.28.0@ohpcd/stable" -c` (note: the bare ref
  `kservice/6.28.0` without user/channel removes *nothing* — conan requires
  the full reference). G2 then rebuilt from source: recipe rev
  `d5dd21e49a5102db6111b7056147c203`, package
  `08ff486632bbe8da1a11f30478317fb8c06bc5a1`
  (full ref `kservice/6.28.0@ohpcd/stable#d5dd21e4...:08ff4866...`).
- **Result**: `VERIFY_RC=0`, Verdict PASS; G0–G4 all PASS. L2/L4/L5 report
  `跳过（无 cache 路径）` (non-blocking): the runner's G4 looks up
  `["Local Cache"][<software>][<full ref>]` while conan 2.29.1's `list
  --format=json` keys `["Local Cache"]` directly by the full reference, so
  the package-id lookup always misses on this conan and the cache path is
  never established (verified with a direct `conan list` probe on the
  device). Equivalent coverage ships through the upstream ctest suite and
  the test_package packaging checks below.
- **Upstream CTest**: `100% tests passed, 0 tests failed out of 6`
  (ksycocatest, ksycoca_xdgdirstest, ksycocathreadtest, kservicetest,
  kapplicationtradertest, kmimeassociationstest; 5.71 s total).
  `ksycocatest` totals: 7 passed, 0 failed, 3 skipped (skips carry printed
  reasons: symlink creation, chmod-then-read, future-mtime — the POSIX fs
  semantics patch 0002 guards on the OHOS user volume).
- **test_package**: consumer suite 13/13 PASS + packaging asserts 10/10 —
  bare `DT_SONAME=libKF6Service.so` (no versioned symlink chain),
  `kbuildsycoca6` DT_NEEDED entries are clean bare basenames,
  `kbuildsycoca6 --version` prints `kbuildsycoca6 6.28.0`.
- **Packaging log**: `Normalized 1 DT_NEEDED entry in bin/kbuildsycoca6`
  (across 1 packaged ELF) and `Signed 2 OHOS package ELF file(s)` — the
  E537 normalization + re-sign path exercised exactly as designed.
- **Artifacts**: `lib/libKF6Service.so` (unversioned real library,
  DT_SONAME bare), `bin/kbuildsycoca6`, KF6Service headers and CMake
  package configs.
- Report: `reports/conan-verify-report.md`. The raw `conan-create.log` is
  not archived (platform rule: only the sanitized md ships in `reports/`).
