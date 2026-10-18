# Analitza

Analitza is the KDE education math library behind kalgebra. It parses and
evaluates mathematical expressions (`libAnalitza`), draws 2D/3D plots with
marching-squares/cubes backends (`libAnalitzaPlot`), and ships Gui-side
models plus QWidget views (`libAnalitzaGui`, `libAnalitzaWidgets`) together
with the `org.kde.analitza` QML module.

## OHOS adaptation

- The published qtbase/6.11.1 line is built without Qt6PrintSupport,
  Qt6OpenGL and Qt6OpenGLWidgets. The top-level `find_package(Qt6)` moves
  those three modules to OPTIONAL_COMPONENTS and every link/compile site
  is guarded by `TARGET` existence (patches 0001-0005).
- `analitzaplot/CMakeLists.txt` resolves the OpenGL capability at configure
  time (`if(TARGET Qt6::OpenGL)`) and exports `ANALITZA_HAVE_OPENGL` (0/1) as
  a PUBLIC compile definition of the AnalitzaPlot target, so the installed
  `plotter3d_es.h` and every CMake consumer compile the same class layout;
  the header keeps a `__has_include(<QOpenGLFunctions>)` fallback for
  non-CMake consumers, and `plotter3d_es.cpp` probes
  `__has_include(<QPrinter>)` (ANALITZA_HAVE_PRINTSUPPORT) (patches 0002 +
  0006). The GL scene and PDF saving are compiled out on this Qt line, while
  the 3D math model and the X3D/STL export path stay intact - the four
  upstream `export-test-*` CTest cases still run.
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` (E330): HMDFS rejects the
  versioned `.so` symlink chain CMake creates after linking, so each
  library ships as a single file under its plain name with a bare
  `DT_SONAME` from the injected `-Wl,-soname` rule (OHOS CMake has no
  SONAME rule of its own).
- `cmake install()` rewrites RUNPATH and invalidates the OHOS `.codesign`
  section, so `package()` re-signs every ELF with
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign
  -selfSign 1`.
- Qt6Svg lives in qtsvg, Qt6Qml/Qt6Quick in qtdeclarative, and those
  packages use `cmake_find_mode=none`; the recipe sets
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`, writes
  `conan_cmakedeps_paths.cmake`, points `ECM_MODULE_PATH` at the ECM
  modules, and pins `Qt6LinguistTools_DIR` from the
  qt6linguisttools/6.11.1 tool requirement.
- Upstream CTest runs inside `conan create` with the build-tree libraries
  mirrored into each test directory (copy fallback - HMDFS cannot symlink),
  `QT_QPA_PLATFORM=offscreen`, isolated HOME/XDG dirs, and
  `/system/lib64` prepended to `LD_LIBRARY_PATH`.

## Dependencies

- Runtime/compile: qtbase (Qt6Core/Gui/Widgets/Xml/Test), qtsvg,
  qtdeclarative (Qml/Quick)
- Build tools: ecm (extra-cmake-modules), qt6linguisttools
- No KF6 framework libraries are linked.

## References

- Homepage: https://invent.kde.org/education/analitza
- Sources: https://download.kde.org/stable/release-service/26.04.0/src/analitza-26.04.0.tar.xz
