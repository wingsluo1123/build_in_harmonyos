# KTX

KTX is the Khronos texture container library and tool set: `libktx` reads and
writes KTX1/KTX2 files, transcodes Basis Universal supercompressed textures and
encodes ASTC blocks, and the accompanying command line tools (`ktx`, `toktx`,
`ktxinfo`, `ktxsc`, `ktx2check`, `ktx2ktx2`) create, inspect, verify and convert
those files. It is the upstream project behind `archives/k/ktx-software/4.4.2`;
this directory archives it under the software name `ktx`, which is the name the
task pool records for version 4.3.2 (`activity: 开源鸿蒙PC专项积分赛-依赖`,
task id 14729).

## Feature overview

- KTX1 / KTX2 container read and write (`libktx`)
- Basis Universal (ETC1S + UASTC) supercompression and transcoding, via the
  vendored `lib/basisu`
- ASTC block encoding, via the vendored `lib/astc-encoder` (NEON backend on
  aarch64)
- zstd / miniz compression, vendored
- Command line tools: `ktx`, `toktx`, `ktxinfo`, `ktxsc`, `ktx2check`,
  `ktx2ktx2`
- Optional OpenGL / Vulkan texture upload helpers, loaded through `dlopen`

## OHOS adaptation

The package builds natively on HarmonyOS PC (OHOS, aarch64, clang 15,
libc++). It needs **no external Conan dependencies** and **one patch**; the
default options produce a static library plus the command line tools.

- **Library type switch differs between upstream versions.** 4.3.2 selects the
  library type with `KTX_FEATURE_STATIC_LIBRARY` and knows nothing about the
  standard `BUILD_SHARED_LIBS` that 4.4.2 uses. The recipe sets both, so the
  intent (static by default) is honoured on either source tree instead of being
  silently ignored on 4.3.2.
- **Version number without git.** The released tarball carries no `.git`, so
  `cmake/version.cmake` degrades to `0.0.0-noversion` and prints a configure
  warning, and `./mkversion` stamps `version.h` with its `DEF_VER=v4.0`
  fallback. Upstream 4.4.2 accepts an explicit `KTX_GIT_VERSION_FULL`
  override and passes the version to `scripts/mkversion -v`; 4.3.2 does
  neither. `patches/0001-ohos-version-header.patch` backports the override
  mechanism to `cmake/version.cmake`, replaces the `DEF_VER` fallback in
  `mkversion` with the real version, and keeps that script's `+x` bit. The
  recipe passes `-DKTX_GIT_VERSION_FULL=v4.3.2`, the same variable the 4.4.2
  recipe uses.
- **The version override must be a command-line `-D`, not a toolchain
  variable.** `cmake/version.cmake` is `include()`d at line 13 of the
  top-level `CMakeLists.txt`, before `project()` at line 25, and CMake only
  reads `conan_toolchain.cmake` at `project()` time — a `CMakeToolchain`
  variable is still empty at line 13.
- **`./mkversion` is run through `${BASH_EXECUTABLE}`.** On a HarmonyOS PC the
  whole conan → cmake → make chain runs in the restricted `adhoc_bin` domain,
  which refuses to start files in the user-storage build tree; running
  `./mkversion` directly fails with `Permission denied` (make Error 126) even
  though the file is mode 0770 and runs fine from an interactive shell.
  `find_package(Bash REQUIRED)` at `CMakeLists.txt` line 11 guarantees
  `BASH_EXECUTABLE`.
- **Vendored dependencies only.** basisu, astc-encoder, zstd, miniz, fmt and
  cxxopts all live inside the source tree, so `requirements()` is empty and the
  package is self-contained.
- **No portability patches are needed.** OHOS clang defines `__linux__` and
  `__aarch64__`, which is exactly what KTX keys on: the Linux `dlopen` upload
  paths and the ASTC NEON backend are selected automatically.
- **`system_libs` matters for C consumers.** `libktx.a` contains C++ objects
  (basisu and astc-encoder are C++), so `package_info()` declares
  `system_libs = ["c++", "dl", "pthread", "m"]`. Without it a plain C consumer
  fails to link with undefined `operator new` / `operator delete`.
- **GL/VK upload off by default.** Both are `dlopen`-based and only needed by
  consumers that upload textures to a GPU; leaving them off keeps the package
  free of link-time graphics dependencies.
- **This is a tool-type package.** The build installs executables into `bin/`,
  so per ARCHIVE-SPEC v3.0 §2.1 the software level carries a `commands.json`.
- **No symlinks in the package.** A static build produces `libktx.a` rather
  than a `libktx.so -> libktx.so.4 -> libktx.so.4.3.2` chain, which is also
  why `conan create` runs unmodified on the restricted `adhoc_bin` domain of a
  HarmonyOS PC workstation (that domain denies symlink creation).

Known differences from a Linux build:

- `ktx --version` reports the version passed in from the recipe
  (`v4.3.2`) instead of a `git describe` result — the same behaviour as the
  already archived 4.4.2 entry.
- `KTX_FEATURE_TESTS=OFF`, matching the merged 4.4.2 recipe, so no `build()`
  step of `conan create` runs upstream's gtest suites. (The CLI suites are a
  different story: upstream registers them under `KTX_FEATURE_TOOLS` alone, so
  the build tree does contain a ctest suite — see `notes.md` for the numbers
  and for the seven environment-bound failures.)
- `KTX_FEATURE_TOOLS_CTS` is left at its upstream default `OFF`; the CTS
  submodule it needs is not part of a source tarball.

## Dependencies

Build dependencies: none beyond the toolchain (cmake 4.1.2, clang 15,
Conan 2.29.1) and the vendored sources.

Runtime dependencies: libc, libc++, libdl, libpthread, libm (declared as
`system_libs`). `bin/ktx` and friends are the only runtime entry points.

## References

- Homepage / source: <https://github.com/KhronosGroup/KTX-Software>
- KTX file format specification: <https://github.khronos.org/KTX-Specification/>
- Sibling archive entry: `archives/k/ktx-software/4.4.2` (same upstream, other
  software name)
