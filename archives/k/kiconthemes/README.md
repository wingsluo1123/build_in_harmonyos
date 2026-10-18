# KIconThemes

KIconThemes is a KDE Frameworks 6 library providing icon theme support on
Qt: KIconLoader for icon loading with theme fallbacks and caching, KIconTheme
for freedesktop icon theme handling, KIconEngine as a QIconEnginePlugin
backed by the theme system, plus KIconButton/KIconDialog widgets and the
KIconWidgets add-on library. Ships `libKF6IconThemes.so` and
`libKF6IconWidgets.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KICONTHEMES_USE_QTQUICK=OFF` and the patched-out `include(ECMQmlModule)`:
  Qt6Qml/Qt6Quick are not part of the qtbase package in this repository.
- `USE_DBUS=OFF`: Qt6DBus is not part of the qtbase package in this
  repository.
- `USE_BreezeIcons=OFF`: KF6BreezeIcons is not published to ohpcd; icons
  still resolve from user-installed themes.
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt6UiPlugin,
  which is not part of the qtbase package in this repository.
- `KF_SKIP_PO_PROCESSING=ON`: no translated catalog payload.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time. The **6.26.0** recipe prepends `/system/lib64` to
  `LD_LIBRARY_PATH` so `qtpaths` resolves the compatible `libc++_shared.so`
  (the sandbox default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`); the 6.18-line recipes do not set
  that entry and configure/`qtpaths` succeed without it.
- Upstream autotests run headless under `QT_QPA_PLATFORM=offscreen`:
  5/5 CTest targets plus the kiconloader_unittest subset (29/29 checks; one
  shared-mime-info data row is unavailable in the current OHOS baseline)
  and the kiconengine_unittest subset (8/8 checks; testMode needs
  BreezeIcons) pass on OHOS.
- **6.18-line karchive pin (`6.18.0.2`)**: the published `kiconthemes/6.18.0`
  recipe revision `f82185f3` pinned the static `karchive/6.19.0`, which
  conflicts with the `karchive/6.18.0` closure that the rest of the 6.18 line
  (`knewstuff/6.18.0`, `libkdegames/26.04.0`, ...) carries. The 6.18-line refs
  require the shared `karchive/6.18.0` instead. kiconthemes only touches
  `KCompressionDevice`, whose header is identical in karchive 6.18.0 and
  6.19.0, and upstream itself requires `KF6Archive >= 6.18.0`
  (`KF_DEP_VERSION`), so no 6.19-only API is used.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0)
- Runtime/compile: qtbase (Qt6Widgets/Qt6Gui/Qt6GuiPrivate), qtsvg,
  karchive, ki18n, kwidgetsaddons, kcolorscheme

## References

- Homepage: https://invent.kde.org/frameworks/kiconthemes
- Sources: https://download.kde.org/stable/frameworks/
