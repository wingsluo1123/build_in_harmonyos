#!/usr/bin/env python3
"""Conan 2.x recipe — poppler 25.12.0

PDF rendering library providing PDF document processing functionality.

Build system: CMake
Patches: 37 patches fixing C++23 std::ranges compatibility (adding std:: prefix)
Dependencies: freetype (system), fontconfig bypassed via FONT_CONFIGURATION=generic
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PopplerConan(ConanFile):
    name = "poppler"
    version = "25.12.0"
    description = "PDF rendering library providing PDF document processing functionality"
    license = "GPL-2.0-or-later"
    homepage = "https://poppler.freedesktop.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # Package options
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Poppler is NOT a system same-name library, so R26 does not apply.
        # Default to shared libraries (controlled by options.shared).
        # CMake build configuration
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        # Font configuration: use generic (no fontconfig dependency on OHOS)
        tc.variables["FONT_CONFIGURATION"] = "generic"
        # Disable optional dependencies not available on OHOS
        tc.variables["ENABLE_BOOST"] = "OFF"
        tc.variables["ENABLE_CPP"] = "ON"
        tc.variables["ENABLE_GLIB"] = "OFF"
        tc.variables["ENABLE_GOBJECT_INTROSPECTION"] = "OFF"
        tc.variables["ENABLE_GTK_DOC"] = "OFF"
        tc.variables["ENABLE_QT5"] = "OFF"
        tc.variables["ENABLE_QT6"] = "OFF"
        tc.variables["ENABLE_UNSTABLE_API_ABI_HEADERS"] = "ON"
        tc.variables["ENABLE_NSS3"] = "OFF"
        tc.variables["ENABLE_GPGME"] = "OFF"
        tc.variables["ENABLE_LIBCURL"] = "OFF"
        # TIFF disabled: system libtiff cmake config exports TIFF::tiff (lowercase)
        # but poppler expects TIFF::TIFF (uppercase). Disable to avoid target mismatch.
        tc.variables["ENABLE_LIBTIFF"] = "OFF"
        # R33: All compiler flags come from CMakeToolchain, not shell env vars
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # R33: No shell environment variable dependencies in build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Main library
        self.cpp_info.libs = ["poppler"]
        # C++ wrapper library
        self.cpp_info.libs.append("poppler-cpp")
