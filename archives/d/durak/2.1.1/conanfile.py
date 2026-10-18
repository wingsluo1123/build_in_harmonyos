#!/usr/bin/env python3
"""Conan recipe for durak 2.1.1 on HarmonyOS PC (aarch64-ohos).

durak is a header-only (INTERFACE) C++20 card-game engine library built
with CMake. It depends on confu_json (JSON struct reflection), Boost
headers and, for the bundled test suite, Catch2 v2.

OHOS toolchain notes (libc++ 15 / clang 15, OHOS SDK 26):
  - libc++ 15 hides C++20 <ranges> algorithms behind
    _LIBCPP_HAS_NO_INCOMPLETE_RANGES unless _LIBCPP_ENABLE_EXPERIMENTAL is
    defined; durak headers use std::ranges::* unconditionally, so the
    define is required both for this build and for consumers.
  - C++23 std::ranges::contains / libc++ std::format runtime symbols are
    absent on OHOS; upstream source is patched (see patches/).
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DurakConan(ConanFile):
    name = "durak"
    version = "2.1.1"
    description = "A header-only C++20 implementation of the Russian card game Durak"
    license = "BSL-1.0"
    homepage = "https://github.com/werto87/durak"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("confu_json/1.2.4")
        self.requires("boost/1.90.0")
        # Catch2 is used only by the bundled upstream test suite built inside
        # conan create (build()); it is not part of the shipped package.
        self.test_requires("catch2/2.13.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Dependencies' CMake config files (confu_json, boost, catch2) must be
        # generated for the upstream CMakeLists find_package() calls to work.
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # durak is a header-only INTERFACE library; nothing to link.
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream requires C++20 (std::ranges); profile default is cppstd=17.
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "20"
        tc.cache_variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # Build and run the bundled Catch2 test suite inside conan create.
        tc.cache_variables["BUILD_TESTS"] = "ON"
        # OHOS libc++ 15 hides <ranges> algorithms unless experimental is on.
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-D_LIBCPP_ENABLE_EXPERIMENTAL"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream Catch2 test suite (W3-local equivalent inside create).
        self.run("ctest --output-on-failure", env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "durak")
        self.cpp_info.set_property("cmake_target_name", "durak::durak")
        self.cpp_info.libs = []
        # durak headers include confu_json, magic_enum and Boost headers, and
        # use std::ranges unconditionally (see OHOS toolchain note above).
        self.cpp_info.requires = ["confu_json::confu_json", "boost::boost"]
        self.cpp_info.defines = ["_LIBCPP_ENABLE_EXPERIMENTAL"]