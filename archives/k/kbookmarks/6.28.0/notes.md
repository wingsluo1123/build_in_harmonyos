# kbookmarks 6.28.0 notes

## Scope

KF6 6.28 train version bump of the existing `kbookmarks` recipe (6.18.0
baseline). Path A (basic adaptation), archive dir `archives/k/kbookmarks/6.28.0`.
No R37 version bump: neither the official main nor the ohpcd registry had a
kbookmarks/6.28.0 entry before this change.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips po/qm catalog generation without a source
  patch: ECM's `ecm_process_po_files_as_qm()` returns early when the option is
  set (verified in the ECM 6.26/6.28 sources on the device), so no
  Qt6LinguistTools discovery happens (not published to ohpcd).
- `patches/0001-CMakeLists.txt.patch` lowers `KF_DEP_VERSION` 6.28.0 ->
  6.26.0, the common floor of the published KF6 stack: ohpcd has kconfig and
  kcoreaddons up to 6.26.0.1 while kwidgetsaddons is at 6.28.0 (kcontacts
  6.28.0 precedent). Single hunk.
- `BUILD_TESTING=ON` enables the upstream autotest suite during the OHOS
  Conan package build.
- `conandata.yml` gives the source URL as an R39 list: official
  download.kde.org URL first, then three authoritative mirrors (FTP.funet.fi,
  mirror.freedif.org, mirrorservice.org). download.kde.org 302-redirects to
  mirrors.bfsu.edu.cn from CN networks, which failed TLS certificate
  verification both on the campus PC and on the device; conan's
  `get()`/`download()` natively treat a URL list as primary + mirrors on
  download error. All four URLs were verified to serve identical bytes
  (sha256 `d7f4048…e3741f5c`, 1093888 bytes each).
- Shared libraries are emitted unversioned through
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` plus explicit `-Wl,-soname,` flags
  (plain + cache variables): HMDFS rejects `symlink()` with EPERM, so CMake's
  versioned `.so` chain cannot be created on device; the ELF still carries a
  real DT_SONAME so consumers record bare sonames (kwidgetsaddons 6.28.0 /
  kitemviews 6.28.0 precedent).
- Dependencies: `qtbase/6.11.1`, `kconfig/6.26.0.1`,
  `kcoreaddons/6.26.0.1`, `kwidgetsaddons/6.28.0`, build tool `ecm/6.28.0`
  (6.28.0 raises the ECM minimum to 6.28.0; published to ohpcd since
  2026-10-14).

## Upstream delta 6.18.0 -> 6.28.0

- `cmake_minimum_required` 3.16 -> 3.29; `REQUIRED_QT_VERSION` 6.7.0 -> 6.9.0;
  ECM minimum 6.18.0 -> 6.28.0; deprecation floors raised (QT 6.10->6.11,
  KF 6.17->6.27); version vars to 6.28.0.
- `src/widgets/CMakeLists.txt`: `KF6::Bookmarks` moved from PRIVATE to
  PUBLIC; no-op for OHOS.
- `src/kbookmark.cpp/.h`: upstream fixes; `autotests/CMakeLists.txt` and
  `tests/CMakeLists.txt` are byte-identical to 6.18.0.

## Verification

- Upstream source sha256 verified on PC (three mirror URLs, identical bytes):
  `d7f4048860ef00bc5d135e284dc6b1307d03199c2c13020994b17e38e3741f5c`; all
  three mirrors were also reachable from the device (HTTP 200, 1093888 B).
- OHOS `conan create` + `conan-verify` (G0-G4) on the device, see
  `reports/conan-verify-report.md` (the full conan-create.log is not shipped
  with the archive per platform policy).
- Upstream CTest: `kbookmarktest` 1/1 (XBEL payload, mime data, external file
  change, manager reload); the `tests/` UI probe is built but not registered
  as a CTest test upstream (`ecm_mark_as_test` only marks it as a test
  target).
- Consumer `test_package` 14/14 checks: add/save/XBEL payload on disk,
  re-open lookup by address, and KBookmarkMenu filling a QMenu (offscreen).
  Note: KBookmarkMenu populates lazily (ctor only connects to
  QMenu::aboutToShow), so the test calls the public `ensureUpToDate()` before
  inspecting `menu.actions()`.
