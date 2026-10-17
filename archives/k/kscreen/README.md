# kscreen

KDE Plasma screen management service.

## Description
Provides the Plasma screen-management actor for HarmonyOS PC: the kded
plugin `lib/plugins/kf6/kded/kscreen.so` (a KDEDModule built on the
published libkscreen 6.7.2 KScreen::Config model and OSD action
serialization) and the `kscreen-console` diagnostic tool. The Plasma
KCM/OSD/plasmoid and the HDR calibrator are not built on OHOS — their
Plasma/PlasmaQuick, LayerShellQt, KF6::KCMUtils/Svg/Crash and Qt6 private
header dependencies are not published.

## Homepage
https://invent.kde.org/plasma/kscreen

## License
GPL-2.0-or-later

## Build System
CMake (KDE ECM)

## Dependencies
- qtbase/6.11.1.2 (pinned with override)
- qtdeclarative/6.11.1
- libkscreen/6.7.2
- kcoreaddons/6.26.0, kdbusaddons/6.18.0, ki18n/6.26.0, kwindowsystem/6.26.0
- ecm/6.26.0 and qt6linguisttools/6.11.1 (build tools)
- dbus 1.14.10 (vendored shared libdbus-1.so.3 for Qt6DBus dlopen)

## Versions
- 6.7.2: initial HarmonyOS PC adaptation (2026-10-15)
