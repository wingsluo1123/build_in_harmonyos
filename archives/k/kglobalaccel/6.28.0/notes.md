# kglobalaccel 6.28.0 notes

## Scope

HarmonyOS PC (aarch64 / OHOS) recipe for KDE Frameworks 6 kglobalaccel
6.28.0 (`libKF6GlobalAccel.so`, `KF6::GlobalAccel`), the KF6 6.28 train
update of the existing 6.26.0 line. Upstream tarball
`kglobalaccel-6.28.0.tar.xz`, sha256
`b40c195ba7e6674898a64f4e3e25e0235dd79682f39395409469274acb580ac0`.
`conandata.yml` fetches it from `mirrors.nju.edu.cn` (KDE official mirror):
the official `download.kde.org` redirect target (`mirrors.bfsu.edu.cn`)
fails TLS verification on the build network. Mirror fidelity was
calibrated and cross-checked byte-for-byte: the nju copy the device
downloaded hashes to `b40c195b…ac0`, identical to the `mirrors.mit.edu`
copy, and the mit mirror's 6.26.0 archive matches the sha256 already
recorded in this repo for the same file (`3f19d22d…17a61`).

kglobalaccel stays **tier 1**: no KF6 library dependencies (ECM only).
The 6.26.0 → 6.28.0 upstream delta touches 6 files (`CMakeLists.txt`
version/deprecation lines, `src/kglobalaccel.cpp/.h/_p.h`, the two D-Bus
interface XMLs). New API: `KGlobalAccel::setInverseShortcutActions()`
(6.27+) with the inverse-actions flag in the D-Bus interface, plus the
internal `kglobalacceld`-named-bus preference (falls back to the session
bus). No build-system restructuring, no new dependencies.

## Dependencies (all verified consumable before starting, R36)

| dep | role | verified |
|---|---|---|
| qtbase-sql-dbus/6.11.1 | Qt6::Core/Gui/Widgets/Test/DBus (qtbase has `FEATURE_dbus=OFF`) | `conan download -r=ohpcd` EXIT=0 |
| qt6linguisttools/6.11.1 | `Qt6::LinguistTools` (lrelease) for `ecm_install_po_files_as_qm(poqm)`, 102 catalogs | EXIT=0 |
| qtdeclarative/6.11.1 | `Qt6::Qml` for the upstream tests/ target | EXIT=0 |
| ecm/6.28.0 | `find_package(ECM 6.28.0 NO_MODULE)` | EXIT=0 |

R37: kglobalaccel/6.28.0 does not exist in the ohpcd registry (the download
probe errors while kglobalaccel/6.26.0 downloads fine) — this is the first
in-repo adaptation of the version, so no version suffix is required.

## Adaptations (recipe layer only — zero source patches)

1. `KF_IGNORE_PLATFORM_CHECK=TRUE` — ECM's `KDEMetaInfoPlatformCheck` reads
   `metainfo.yaml` (platforms: Linux, FreeBSD) and aborts configure on
   HarmonyOS.
2. `WITH_X11=OFF` — upstream defaults it ON and `src/kglobalaccel.cpp`
   includes `<private/qtx11extras_p.h>`; the OHOS Qt builds ship
   `FEATURE_xcb/xlib=OFF` and no such private header.
3. `qtbase-sql-dbus/6.11.1` as the Qt6 provider — the only OHOS package
   shipping `lib/cmake/Qt6DBus` + `libQt6DBus.so`.
4. `ECM_MODULE_PATH` set explicitly + hand-written
   `conan_cmakedeps_paths.cmake` (qtbase uses `cmake_find_mode=none`), with
   qtbase-sql-dbus ordered first.
5. `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` lists every Qt package folder so
   `find_package(Qt6 COMPONENTS LinguistTools)` resolves across Conan
   package folders.
6. Build/test runtime environment: prepend `/system/lib64` and the OHOS SDK
   `llvm/lib` to `LD_LIBRARY_PATH` (kconfig 6.26.0 precedent) so `qtpaths`
   and the poqm tools resolve a compatible `libc++_shared.so`.
7. OHOS shared-library rules are SONAME-only: the recipe writes a
   `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` rules file defining only
   `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`/`_CXX_FLAG` (`-Wl,-soname,`) and
   sets `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`. Rationale: with the
   `CMAKE_SHARED_LIBRARY_RUNTIME_*` flags defined, cmake's `install()`
   rewrites the ELF and strips the RUNPATH, after which the device loader
   rejects dlopen (EACCES); HMDFS additionally rejects symlink(2), so the
   versioned-symlink chain cannot materialize. With SONAME-only rules the
   package ships an unversioned `libKF6GlobalAccel.so` with the basename
   DT_SONAME and `install()` is a byte-identical copy.
8. `BUILD_TESTING=ON` so the upstream tests/ entry point compiles (it is
   the only upstream test artifact; see the R51 declaration below).

## R51 upstream test declaration (three steps)

**Step 1 — inventory.** `tests/` = `CMakeLists.txt` +
`kglobalacceltest.cpp` + `kglobalacceltest.qml`. The CMakeLists declares
only `add_executable(kglobalacceltest …)` (links KF6::GlobalAccel Qt6::Qml
Qt6::Test); **no `add_test()`** → 0 CTest-registered cases
(`ctest -N` → `Total Tests: 0`).

**Step 2 — run.** Executed on the device: `ctest -N` → `Total Tests: 0`;
the single target `kglobalacceltest` was built and launched offscreen
(rc=124 under a 15 s timeout = event loop reached, no crash; only the
`org.kde.kquickcontrols` QML module is unavailable). Full evidence in the
Verification section below.

**Step 3 — report.** Upstream automated cases 0, passed 0, failed 0. The
single entry point is a non-checking GUI/QML program that never returns;
its QML scene needs `org.kde.kquickcontrols` (from kdeclarative, which
reverse-depends on kglobalaccel — cycle), so the executable is reported as
"launched, event loop reached, no crash" instead of a passing case.

`test_package` is not used as a substitute for upstream statistics; it is
declared separately (3 consumer cases / 10 checks, non-zero exit on any
failure).

## Verification

Device conan-verify run on HarmonyOS PC aarch64 (2026-10-17, `VERIFY_RC=0`,
report Verdict **PASS**):

- Gates: G0 PASS, G1 PASS (12 recipe-integrity checks), G2 PASS (clean
  `conan create`), G3 PASS (no system same-name library conflict), G4 PASS;
  L2/L4/L5 reported skip by the tool ("no cache path", see the
  package-identity checks below for the equivalent manual evidence).
- Build chain inside `conan create`: source fetch from
  `mirrors.nju.edu.cn` (sha256 `b40c195b…ac0`) → CMake configure
  (SONAME-only rules file installed via
  `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` + `CMAKE_PLATFORM_NO_VERSIONED_SONAME`)
  → build (102 poqm translation catalogs, `kglobalacceltest` target
  built) → `cmake --install` → test_package.
- R51 step 2 evidence (real device runs):
  - `ctest --test-dir <conan build dir> -N` → `Total Tests: 0` (upstream
    `tests/CMakeLists.txt` declares no `add_test`).
  - `kglobalacceltest` (the only test target) builds and launches
    offscreen (`QT_QPA_PLATFORM=offscreen` + the conan-generated runtime
    env): the QML engine reports exactly one missing module —
    `module "org.kde.kquickcontrols" is not installed` (provided by
    kdeclarative, which reverse-depends on kglobalaccel). With
    `QML2_IMPORT_PATH` pointed at the qtdeclarative `qml/` tree, QtQuick
    and QtQuick.Controls resolve and only the kquickcontrols module
    remains unavailable. The process then stays in its event loop and is
    killed by the 15 s timeout → `rc=124` = event loop reached, no crash.
- test_package: 3 consumer cases / 10 checks executed through the direct
  binary run (`./test_kglobalaccel`, E298: no CTest delegation), result
  `TEST SUMMARY: 3 passed, 0 failed`; non-zero exit on any failure.
- Package identity: recipe revision
  `a2704e9ec5d4c15c260ef63857fb5456`, package_id
  `abf064d3b52a706f3e5651d0de7f2b3a1c8c7d03`, package revision
  `2f45de46d13a7371bf1df49197568c70`.
- Artifact checks (`readelf -d` / `cmp` on the device):
  - `lib/libKF6GlobalAccel.so` is a single unversioned file — no
    versioned symlink chain (HMDFS rejects `symlink(2)`).
  - `DT_SONAME = libKF6GlobalAccel.so` (plain basename); no
    RPATH/RUNPATH entries; `DT_NEEDED` are plain basenames
    (`libQt6Widgets.so.6`, `libQt6Gui.so.6`, `libQt6DBus.so.6`,
    `libQt6Core.so.6`, `libc++_shared.so`, `libc.so`).
  - `cmp` of the build artifact vs the installed file →
    byte-identical (358976 bytes each): `install()` is a pure copy
    (no ELF rewrite, RUNPATH preserved/absent as built).

## Caveats

- Real shortcut registration needs a session D-Bus (kglobalacceld); the
  library degrades gracefully without one and the consumer executor is
  written against API-consistency state so it is deterministic headless.
- The X11 code path is compiled out (`WITH_X11=OFF`).
