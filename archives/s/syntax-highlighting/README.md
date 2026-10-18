# Syntax Highlighting

Syntax Highlighting is the KDE Frameworks 6 syntax highlighting engine behind
Kate, KWrite and other consumers: it loads the shared Kate syntax definition
files, applies contextual highlighting rules and themes, and exposes the
`KSyntaxHighlighting::{Repository,Definition,Theme,Highlighter}` public API.
Ships `libKF6SyntaxHighlighting.so` (plus the upstream `ksyntaxhighlighter6`
CLI, which this package does not declare).

This directory hosts the `syntax-highlighting` Conan package (KDE Frameworks
6.28 line). The historical `archives/k/ksyntaxhighlighting/` line keeps its
own package name and versions.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt6LinguistTools is not
  part of the qtbase package in this repository.
- The `BUILD_EXAMPLES` option is patched in and set to `OFF`: the example
  applications (KWrite-like demo widgets) are not needed for library
  packaging.
- `QRC_SYNTAX=ON` embeds the syntax definitions and themes into the library
  as Qt resources, so consumers need no external data files at runtime.
- `katehighlightingindexer.cpp` uses `std::strong_ordering` (C++20). The
  `compiler.cppstd=17` profile value is written as a normal variable into
  `conan_toolchain.cmake` and shadows the recipe-injected CACHE
  `CMAKE_CXX_STANDARD=20`, so the CMakeLists patch pins
  `set(CMAKE_CXX_STANDARD 20)` inside the project; `CMAKE_CXX_FLAGS=-std=c++20`
  is kept as a belt-and-braces fallback in the recipe.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- The upstream autotests (6 CTest entries, including
  `testhighlighter_test` and `htmlhighlighter_test`) run headless under
  `QT_QPA_PLATFORM=offscreen` and pass 6/6 on OHOS.

## Dependencies

- Build: ecm (extra-cmake-modules) 6.28.0, perl 5.42.2, CMake >= 3.29
- Runtime/compile: qtbase (Qt6Core, Qt6Network, Qt6Gui, Qt6Test)

## References

- Homepage: https://invent.kde.org/frameworks/syntax-highlighting
- Sources: https://download.kde.org/stable/frameworks/ (mirrored at
  https://mirrors.nju.edu.cn/kde/stable/frameworks/)
