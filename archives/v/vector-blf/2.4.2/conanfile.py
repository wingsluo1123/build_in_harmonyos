#!/usr/bin/env python3
"""Conan recipe — vector-blf 2.4.2 (Vector Binary Log File support library).

Upstream: CMake project, one shared library target `Vector_BLF`
(`src/Vector/BLF/CMakeLists.txt` hard-codes `add_library(... SHARED ...)`,
SOVERSION 2 / VERSION 2.4.2).

OHOS adaptation notes (see notes.md for the full evidence):
  * The only external dependency is zlib (`find_package(ZLIB REQUIRED)`), used by
    LogContainer for the compressed log containers of a BLF file.  Conan supplies
    the OHOS zlib static archive, so the compression code ends up inside
    libVector_BLF.so and consumers need no extra runtime library.
  * `OPTION_RUN_DOXYGEN` defaults to ON upstream, which pulls in Doxygen and
    Graphviz (`find_package(Doxygen REQUIRED)`).  Both are documentation-only and
    unavailable in the build environment, so the option is turned off; the
    library itself is not affected.
  * `OPTION_BUILD_TESTS` stays at its upstream default (OFF): the upstream suite
    is 126 Boost.Test binaries that link the compiled Boost.Test libraries, which
    are not part of the OHOS Boost package.  The test inventory and the separate
    R51 run of that suite are documented in notes.md.
  * On OHOS the OHOS SDK clang reports the target as aarch64-unknown-linux-ohos,
    which CMake maps to the (third-party) `HarmonyOS` system; CMake has no
    soname/version support for that system, so the produced file is a plain
    `libVector_BLF.so` without a SONAME and without the usual `.so.2` symlink
    chain.  This is exactly what the packaging below expects.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class VectorBlfConan(ConanFile):
    name = "vector-blf"
    version = "2.4.2"
    description = "Library to access Binary Log File (BLF) files from Vector Informatik"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Technica-Engineering/vector_blf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # LogContainer uses zlib (compress2/uncompress) for compressionMethod 2.
        self.requires("zlib/1.3.2.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The upstream CMakeLists resolves zlib with find_package(ZLIB) and then
        # uses the legacy ${ZLIB_LIBRARIES} variable.  CMakeDeps has to be
        # generated explicitly: without it the build folder gets no
        # ZLIBConfig.cmake, find_package(ZLIB) falls back to the built-in
        # FindZLIB module and happily links whatever "libz" the host happens to
        # expose (on this device: a shared zlib-ng from ~/.harmonybrew/lib),
        # which both violates R26 (system name, must be static) and makes the
        # package depend on a path that does not exist on the CI worker.
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # Documentation targets (Doxygen/Graphviz) are not part of the library
        # build and are not present in the build environment.
        tc.variables["OPTION_RUN_DOXYGEN"] = False
        # Upstream Boost.Test suite (126 binaries) is not built as part of the
        # package; upstream default is OFF, kept explicit for reproducibility.
        tc.variables["OPTION_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["Vector_BLF"]
