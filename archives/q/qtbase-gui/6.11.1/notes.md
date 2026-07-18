# qtbase-gui 6.11.1 HarmonyOS PC notes

## Scope

This package is a dedicated Qt foundation for modules that need graphical Qt
APIs. It intentionally uses the Conan name `qtbase-gui` so it does not collide
with the separate Core-only `qtbase/6.11.1` prerequisite.

Built modules:

- Qt Core
- Qt Network
- Qt Gui
- Qt Widgets, including QGraphicsView support
- Qt Xml

## Reduced platform surface

The package uses Qt's raster functionality and bundled third-party libraries.
External desktop or graphics stacks are disabled: XCB/Xlib, OpenGL/EGL,
Vulkan, DBus, CUPS/PrintSupport, GTK, fontconfig, libinput, evdev and tslib.
This keeps the package independent of a window server while retaining the real
Gui and Widgets libraries required by Qt Charts.

## HarmonyOS adaptations

The five portability patches are derived from the already CI-validated qtbase
PR #2889:

1. Recognize HarmonyOS as a Linux-compatible UNIX platform.
2. Add the `harmonyos-clang` mkspec.
3. Disable unavailable pthread cancellation paths through a capability macro.
4. Reuse CMake's Linux shared-library rules for SONAME and RPATH behavior.
5. Skip Qt's pre-project Android autodetection for the HarmonyOS mkspec.

Installed shared libraries are re-signed after CMake installation because
RPATH changes invalidate the original HarmonyOS code signature.

## Test strategy

The consumer test deliberately does not create `QApplication` and requires no
display server. It validates `QColor`, `QHostAddress`, and the Qt Widgets value
type `QSizePolicy`, proving that Core, Network, Gui and Widgets headers and
libraries are present and linkable.
