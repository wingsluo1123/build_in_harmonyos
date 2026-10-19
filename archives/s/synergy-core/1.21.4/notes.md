# synergy-core 1.21.4 adaptation notes

## Source closure

- Main release: `v1.21.4` tarball from
  `https://github.com/symless/synergy-core/archive/refs/tags/v1.21.4.tar.gz`
  (sha256 `369d789ae5616e6e43b5eeb6feac644ab7d3384c138748a13ed9f7e1df7361a6`).
- No submodules are consumed: the 1.21.4 tarball vendors everything
  in-tree. Unlike 1.20.4 there is no `synergy-extra` and no GoogleTest
  fetch — the upstream test framework is Qt Test (`QTEST_MAIN` /
  `create_test()` in `src/unittests/`), provided by the Qt anchor.

## Delivery shape: core-lib + cli, desktop GUI trimmed

- `BUILD_GUI=OFF` trims `src/apps/deskflow-gui`, `src/lib/gui` (and with it
  the 4 gui test executables, which link the trimmed `src/lib/gui` library)
  and `extra/src/lib/synergy/gui` (the extra tree gates its gui subdir
  behind `BUILD_GUI` upstream).
- `src/apps/deskflow-daemon` is Windows-only upstream and never builds on
  Unix.
- The unified `synergy-core` CLI (server + client in one binary) is the
  delivered artifact.
- The X11 platform backend (`src/lib/platform/XWindows*`) is kept at the
  library layer via `BUILD_X11_SUPPORT=ON` against the conan-published X11
  client libraries — the same delivery shape as the in-repo barrier/2.4.0
  (synergy's direct upstream fork).

## Qt resolution: 5.15 through the version-agnostic upstream path

- Upstream calls `find_package(QT NAMES Qt6 Qt5 REQUIRED ...)` and ships
  the Qt5→Qt6 `add_library(Qt6::X ALIAS Qt5::X)` bridge itself
  (`cmake/Libraries.cmake`), plus `VersionOverrides.cmake` honors
  `QT_VERSION_OVERRIDE` (the el8 CI leg precedent for building against
  Qt 5.13). The recipe sets `QT_VERSION_OVERRIDE=5.15`.
- `qt5-qtbase/5.15.2.2` is the Qt anchor: it publishes the
  Core/Gui/Widgets/Network/Xml/DBus/Test modules with per-module
  `Qt5XConfig.cmake` files, the `moc`/`rcc`/`uic` host tools, and the
  `minimal`/`offscreen` platform plugins.
- AUTOMOC needs the tool path injected (`CMAKE_AUTOMOC_EXECUTABLE`,
  attica5/dewalls precedent) because qt5-qtbase exports no `Qt5::moc`
  executable target. AUTOMOC also needs `LD_LIBRARY_PATH` to resolve
  `libc++_shared.so`/`libQt5Core.so` when executing the OHOS-ELF moc.
- The conan profile pins `cppstd=17`; upstream requires C++20
  (`using Container::size_type` without typename and `using enum` are both
  C++20). `configure()` raises `settings.compiler.cppstd=20` (apache-arrow
  25.0.0 precedent). Note: raising it only through toolchain variables is
  not enough — the OHOS conan toolchain appends `-std=c++17` after
  `CMAKE_CXX_FLAGS` injections and the trailing flag wins.
- One genuine clang-vs-GCC divergence survives even in C++20 mode: a
  `typename` is still required before a dependent type name on a
  type-alias right-hand side (`using value_type = Container::value_type`
  compiles under GCC, not under clang 15 — P0634 does not cover that
  position). Patched in `PriorityQueue.h`.

## X11 client libraries and the CMake probe path

- `barrier/2.4.0` precedent end to end: the OHOS conan toolchain sets
  `CMAKE_SYSTEM_NAME=HarmonyOS`, but CMake has no HarmonyOS platform
  module, so `UNIX` is empty and every Linux branch (X11 detection, the
  XWindows platform sources, the Unix arch) would be skipped. The recipe
  forces `CMAKE_SYSTEM_NAME=Linux`.
- The X11 headers and libraries live in conan packages outside the
  compiler's default search path. Two injection channels are needed:
  - `CMAKE_REQUIRED_INCLUDES`/`CMAKE_LIBRARY_PATH` for the module-mode
    probes (`check_include_files`, `check_library_exists`), patched to
    append instead of overwrite the BSD-oriented defaults;
  - `SYNERGY_CONAN_INCLUDE_DIRS`/`SYNERGY_CONAN_LIB_DIRS` cache variables
    applied as directory-level `include_directories()`/`link_directories()`
    in the patched `cmake/Libraries.cmake`, because the toolchain rewrites
    the `*_FLAGS`/`*_INIT` blocks from the profile and the plain
    `CMAKE_CXX_FLAGS_INIT` injection does not survive into target compile
    command lines.
- All X11 probes pass: Xlib/XKBlib/Xinerama/Xrandr/XTest/Xi2 headers and
  the Xtst/Xext/Xinerama/Xrandr/Xi/SM/ICE library functions.

## Dependencies deliberately absent

- `libxrandr`: the optional display-hotplug extension. Every use site is
  guarded by the `HAVE_X11_EXTENSIONS_XRANDR_H` probe (the patched
  cmake/Libraries.cmake normalizes the absent probe to 0), so removing the
  library just disables the hotplug path — the same delivery as the
  in-repo barrier/2.4.0. Keeping it would pull libxrender, whose published
  binary was built against the libx11/1.8 graph while this graph pins
  libx11/6.4 (libxtst/libxi/libxinerama), forcing CI workers to build
  libxrender from source — which deterministically trips their
  fork-exhaustion fault during the autotools configure (observed across
  workers CI-003/006/020/030 in five consecutive rounds).

- `glib`: only the libportal sources consume it and they are not selected
  in this X11-only delivery (LIBEI/LIBPORTAL are QUIET probes upstream and
  find nothing). The conan glib package's `.pc` also drags a musl-specific
  `-L/lib -l:ld-musl-aarch64.so.1` linker flag that lld cannot resolve on
  this platform — it poisoned every executable link until removed from
  both the graph and the `pkg_check_modules` call.
- `libei`/`libportal`: available in the registry but intentionally not
  required; the Ei/Portal platform legs are alternative input backends and
  upstream treats them as optional.

## Toolchain-borne source adjustments

- `std::ranges` algorithms (push_heap/pop_heap/make_heap,
  lexicographical_compare, set_difference, find_if, partial_sort, find,
  fill, for_each) do not exist in clang 15's libc++; all nine files express
  the same operations through the classic iterator-pair algorithms.
- `std::make_shared<T[]>(n)` (array form, P0970) is missing in clang 15's
  libc++; the pollfd array is allocated through `new T[n]()` wrapped in
  the `shared_ptr` array deleter (same zero-initialization semantics).
- `pthread_setcancelstate`/`pthread_setcanceltype` are not declared by the
  OpenHarmony libc (verified with a sysroot probe: implicit-function
  declarations). Deskflow cancels threads cooperatively through its own
  `m_cancel` flag plus `pthread_kill(SIGWAKEUP)`, so the deferred-cancel
  initialization in the thread entry is dropped.
- The qt5-qtbase package is built with `-no-feature-sharedmemory`, which
  defines `QT_NO_SHAREDMEMORY` and removes the `QSharedMemory` class. The
  single-instance duplicate check in `deskflow-core.cpp` is guarded with
  `#if !defined(QT_NO_SHAREDMEMORY)`; without the feature every invocation
  simply runs (the `--new-instance` flag's behavior becomes the default).
- `install(TARGETS ... RUNTIME_DEPENDENCY_SET)` is rejected by the
  OHOS-hosted CMake for non-Windows systems (the check keys off the host
  system name, not the target's); the dependency set only feeds the WIN32
  DLL deploy, so the install is gated behind `WIN32`.
- Qt5 does not transitively provide `<QRegularExpression>` through the
  headers the test suites include (Qt6 does); the includes are added
  explicitly in `SettingsTests.cpp` and `LogTests.cpp`.

## Upstream tests

- Upstream registers 31 `create_test()` suites in `src/unittests/`. In this
  headless X11 delivery:
  - 22 suites are built and executed (base×6, client×1, common×2 of 3,
    deskflow×7, net×3, platform×1, server×2);
  - 4 gui suites are trimmed together with `src/lib/gui`
    (LoggerTests, KeySequenceTests, config/ScreenTests,
    core/NetworkMonitorTests — they link the trimmed gui library);
  - 3 suites are platform-inapplicable (MSWindowsClipboardTests,
    OSXClipboardTests, OSXKeyStateTests — upstream `if(WIN32)/elseif(APPLE)`
    branches);
  - 1 suite is libei-gated (EiKeyStateTests — `if(LIBEI_FOUND)`);
  - 1 suite is excluded through `SKIP_I18N_TESTS` (I18NTests — the suite
    copies the compiled `deskflow_*.qm` catalogues, and this toolchain
    provides no Qt LinguistTools/lrelease to produce them).
- Measured result (conan create, executed on the build host):
  `100% tests passed, 0 tests failed out of 22` — 148 Qt Test functions
  passed, 0 failed, 1 skipped. The single skip is
  `XWindowsClipboardTests::initTestCase`, which upstream itself QSKIPs on
  hosts with no X display ("no X display available (e.g. headless CI)").
  The suite's `defaultCtor` function still runs and passes.
- The consumer test (`test_package`) exercises the installed CLI's
  contract: `--version` prints the 1.21.4 version string, `--help` prints
  the usage text with the `coremode` positional, and the no-mode
  invocation prints usage and exits 0.

## Local verification

- `conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 --build=missing`
  completes green: package `synergy-core/1.21.4`
  (package id `5903f4c5671c03c1a5bb4d3218d3fcdd0d1f17ae`) is created and
  the test_package consumer checks pass.
- The build runs with `tools.build:jobs=2` (memory-constrained CI workers)
  and `unset LD_LIBRARY_PATH` before invoking conan (the profile's SDK
  paths are re-added by conan; a stale exported value breaks the
  OHOS-ELF host tools).
