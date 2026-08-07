# Qt5 Charts

Qt Charts module for Qt5 5.15.2, providing chart types for data visualization.

## Build Notes
- Requires: qt5-qtbase (with Widgets), qt5-qtdeclarative
- Platform: HarmonyOS (aarch64)
- Build system: qmake (Qt5 addon module)
- Source: No source modifications required for HarmonyOS

## Dependencies
- qt5-qtbase/5.15.2 (Qt Core, Gui, Widgets, Network)
- qt5-qtdeclarative/5.15.2 (Qml, Quick, QmlModels)

## Status
- Conan recipe created (conanfile.py + conandata.yml + test_package/)
- Build blocked by missing dependency: qt5-qtdeclarative/5.15.2 not in Conan remote
- qt5-qtbase/5.15.2 in remote lacks Widgets module (built with -no-widgets)
