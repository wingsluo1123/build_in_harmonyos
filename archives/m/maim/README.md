# maim

maim (make image) is a C++ command-line utility that takes a screenshot of an
X11 desktop. It can capture the root window, a specific window, an explicit
geometry, or an interactively selected region (through slop), and encode the
result as PNG, JPEG, BMP or WebP.

## Features

- Capture the whole desktop, a single window, or an explicit geometry.
- Interactive region/window selection through slop.
- Optional cursor compositing and multi-monitor masking.
- PNG, JPEG, BMP and WebP output, to a file or to standard output.

## HarmonyOS adaptation

The build resolves every dependency through Conan `CMakeDeps` targets instead of
the legacy `modules/Find*.cmake` helper scripts (whose `FindSLOP.cmake` requires
GLX, which HarmonyOS PC does not provide). `cmake_minimum_required` is raised so
CMake 4.x accepts the project, and the target is compiled as C++17 to match the
OHOS profile's `cppstd` and the C++17 requirement of the ICU 76 headers used by
the optional unicode support in `cxxopts`.

## Dependencies

- libx11/6.4.0
- libxext/6.4.0
- libxrender/0.9.12
- libxfixes/6.1.0
- libxcomposite/0.4.6
- libxrandr/1.5.5.1
- libpng/1.6.58.3
- libjpeg-turbo/3.2.0.1
- libwebp/1.6.0.1
- slop/7.7
- glm/1.0.3
- icu/76.1

## References

- https://github.com/naelstrof/maim
