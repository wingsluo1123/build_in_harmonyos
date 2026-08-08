# Test Report — qt5-qtgraphicaleffects 5.15.2
## Build
- Build system: qmake (Qt5 addon module)
- Compiler: clang 15.0.4
- Platform: OpenHarmony aarch64
- Build result: SUCCESS
## Dependencies
- qt5-qtbase/5.15.2.1 (Conan)
- qt5-qtdeclarative/5.15.2 (Conan)
## Artifacts
- qml/QtGraphicalEffects/libqtgraphicaleffectsplugin.so
- qml/QtGraphicalEffects/private/libqtgraphicaleffectsprivate.so
- 25 QML effect files
## Test Results
- Conan verify (G1-G4, L2/L4/L5): PASS
- W3 local CI simulation: PASS
