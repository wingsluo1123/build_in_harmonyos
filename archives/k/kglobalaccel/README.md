# kglobalaccel

KDE Frameworks global-shortcut framework: the KF6 branch builds
libKF6GlobalAccel.so; the KF5 branch (5.116.0) builds libKF5GlobalAccel.so.
Provides application-global keyboard shortcuts that work independently of the
focused window, plus the `KDED`-side registration interface over D-Bus.

- Upstream: https://invent.kde.org/frameworks/kglobalaccel
- License: LGPL-2.0-or-later
- Build system: CMake (ECM / KDEInstallDirs)
- Tier: 1 (`type: integration`, `cmakename: KF6GlobalAccel`)

## Adapted versions for HarmonyOS PC (aarch64)

| Version | Status | Notes |
|---------|--------|-------|
| 5.116.0 | built  | KF5 branch (Qt5): qt5-qtbase/5.15.2.2 (Qt5::DBus + Qt5::Widgets) + qt5-qtdeclarative/5.15.2 (tests) + ecm/6.26.0 (tool); BUILD_RUNTIME=OFF excludes the X11/XCB-only kglobalacceld daemon and its KF5Config/CoreAddons/Crash/DBusAddons/WindowSystem dependency block |
| 6.26.0  | built  | First HarmonyOS PC adaptation: qtbase-sql-dbus 6.11.1 (Qt6::DBus) + qt6linguisttools 6.11.1 (poqm) + qtdeclarative 6.11.1 (tests) + ecm 6.26.0 |
| 6.28.0  | built  | KF6 6.28 train: same dependency set with ecm/6.28.0; OHOS shared-library rules are SONAME-only (unversioned .so with basename DT_SONAME, no versioned symlink chain — HMDFS rejects symlink(2)); upstream 6.27+ setInverseShortcutActions API covered by the consumer executor |

## OHOS adaptation notes

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (metainfo.yaml lists Linux/FreeBSD only; ECM aborts configure on
  HarmonyOS otherwise).
- `WITH_X11=OFF` disables the X11 code path: upstream defaults it ON and
  `src/kglobalaccel.cpp` then includes `<private/qtx11extras_p.h>`, which the
  OHOS qtbase / qtbase-sql-dbus builds do not ship (FEATURE_xcb/xlib=OFF).
- `Qt6::DBus` is provided by `qtbase-sql-dbus/6.11.1`; `qtbase/6.11.1` is
  built with `FEATURE_dbus=OFF` and ships no `Qt6DBus` cmake module.
- `qt6linguisttools/6.11.1` supplies `Qt6::LinguistTools` (lrelease), which
  `ecm_install_po_files_as_qm(poqm)` requires (102 translation catalogs).
  Qt's split-module packages are announced through
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`.
- `qtdeclarative/6.11.1` supplies `Qt6::Qml` for the upstream tests target.
- No source patches are applied — the recipe layer alone is enough.
- The 6.28.0 recipe writes a `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` rules
  file with only `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG` (`-Wl,-soname,`)
  and sets `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`: the package ships an
  unversioned `libKF6GlobalAccel.so` with a basename `DT_SONAME` and
  `install()` is a byte-identical copy. HMDFS rejects `symlink(2)`, so the
  versioned chain cannot materialize; with `CMAKE_SHARED_LIBRARY_RUNTIME_*`
  defined, `install()` would rewrite the ELF and strip the RUNPATH, after
  which the device loader rejects `dlopen` with EACCES.
- Library package: no bin/ artifacts, no commands.json needed (R38).
