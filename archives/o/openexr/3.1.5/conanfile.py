#!/usr/bin/env python3
"""Conan recipe for openexr 3.1.5.

OpenEXR is a high dynamic-range (HDR) image file format developed by
Industrial Light & Magic. It provides 16-bit half and 32-bit float pixel
depths, lossless compression, multi-channel support, and rich metadata.

Build system: CMake.
Dependencies: zlib/1.3.1.1, imath/3.2.2 (managed by Conan instead of CMake
auto-download).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class OpenexrConan(ConanFile):
    name = "openexr"
    version = "3.1.5"
    description = "High dynamic-range (HDR) image file format"
    license = "BSD-3-Clause"
    homepage = "https://github.com/AcademySoftwareFoundation/openexr"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("imath/3.2.2")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"openexr supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # Prevent CMake from auto-downloading Imath; use Conan-provided Imath
        tc.variables["OPENEXR_FORCE_INTERNAL_IMATH"] = "OFF"
        # Fix SONAME on HarmonyOS (CMake doesn't recognize OHOS platform)
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        # RPATH for installed libraries
        tc.variables["CMAKE_SKIP_RPATH"] = "OFF"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"
        # Fix: OpenEXRCore includes <ImathConfig.h> without Imath/ prefix.
        # Add Imath include dirs to C/CXX flags so all targets find ImathConfig.h
        import os
        imath_folder = self.dependencies["imath"].package_folder
        imath_inc = f"-I{imath_folder}/include -I{imath_folder}/include/Imath"
        tc.variables["CMAKE_C_FLAGS"] = imath_inc
        tc.variables["CMAKE_CXX_FLAGS"] = imath_inc
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = [
            "OpenEXR-3_1",
            "OpenEXRCore-3_1",
            "OpenEXRUtil-3_1",
            "Iex-3_1",
            "IlmThread-3_1",
        ]
        self.cpp_info.set_property("cmake_file_name", "OpenEXR")
        self.cpp_info.set_property("cmake_target_name", "OpenEXR::OpenEXR")
        self.cpp_info.requires = ["zlib::zlib", "imath::imath"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
