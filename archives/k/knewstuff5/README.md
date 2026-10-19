# knewstuff5 (KNewStuff KF5)

KNewStuff is the KDE Frameworks 5 "Get Hot New Stuff" framework. It allows
applications to download and install extra content (themes, wallpapers,
plugins, etc.) from remote servers.

This OHOS port ships the scoped-down KF5NewStuffCore library, the qtquick
QML plugin (`org.kde.newstuff`), and the `knewstuff-dialog` tool.  The
widgets layer is not yet available because it depends on KIO / KService /
XmlGui and other KF5 components that have not been published on OHOS.

## OHOS adaptation (KF5 / Qt5 chain)

- **Scoped build** (`KNEWSTUFF_OHOS_SCOPED=ON`): only `KF5NewStuffCore` +
  qtquick plugin + `knewstuff-dialog` are built; widgets layer targets are
  skipped.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KF_SKIP_PO_PROCESSING=ON`: translation catalog generation is skipped
  because Qt5LinguistTools is not in the packaged OHOS Qt5 build.
- **Runtime loader fixes** (E505 + E212/DRAFT-7939): upstream ctest cannot
  run on OHOS with the default LD_LIBRARY_PATH strategy because:
  1. musl loader's `LD_LIBRARY_PATH` overrides `DT_RPATH` and cannot
     resolve versioned soname symlinks (E505);
  2. HMDFS MAC policy requires every `.so` to carry a valid code
     signature, which conan copy operations may invalidate (E212).
  The recipe materialises every runtime dependency as a real file in
  `build/runtime-mirror/`, self-signs each copy with `binary-sign-tool`,
  and adds that single directory to `LD_LIBRARY_PATH`.
- **Upstream tests**: 3/3 pass (`knewstuffauthortest`,
  `knewstuffenginetest`, `installationtest`) — all core/ autotests.

## Dependencies

- `qt5-qtbase/5.15.2.2`
- `qt5-qtdeclarative/5.15.2`
- `attica5/5.116.0`
- `karchive5/5.116.0`
- `kconfig5/5.116.0`
- `kcoreaddons5/5.116.0`
- `ki18n5/5.116.0`
- `kpackage5/5.116.0`
- `kirigami2/5.116.0`
