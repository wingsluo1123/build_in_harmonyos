#!/usr/bin/env python3
"""Conan recipe for libheif 1.18.2 (CMake).

libheif is a library for decoding and encoding HEIF/HEIC image files.
It supports HEVC (via libde265), AV1, JPEG, and other codecs.

This recipe builds the static library plus the CLI tools (heif-info,
heif-dec/heif-convert, heif-enc). Only the libde265 decoder backend is
enabled; all other optional codec backends (aom, x265, dav1d, rav1e,
jpeg, openjpeg) are disabled to keep the dependency graph minimal.

Platform note (aarch64/OHOS): CMake auto-detects the system as unknown
("HarmonyOS"); libheif's CMakeLists.txt handles this gracefully. The
find_package(LIBDE265) module uses pkg-config, which Conan's
PkgConfigDeps generator satisfies via the libde265 dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibheifConan(ConanFile):
    name = "libheif"
    version = "1.18.2"
    description = "Library for decoding and encoding HEIF/HEIC image files"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libde265 provides the HEVC decoder backend (built-in, not plugin).
        self.requires("libde265/1.0.18@ohpcd/stable")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: all build configuration is passed via CMakeToolchain variables,
        # not via shell environment variables.
        tc = CMakeToolchain(self)
        # R26: system-name library defaults to static to avoid polluting
        # /lib or /lib64 with a same-named shared object.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Only pass CMAKE_INSTALL_PREFIX implicitly via conan layout (R1).
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        # Enable libde265 decoder backend (found via pkg-config from Conan dep).
        tc.variables["WITH_LIBDE265"] = "ON"
        # Disable all other codec backends to keep deps minimal.
        tc.variables["WITH_DAV1D"] = "OFF"
        tc.variables["WITH_AOM_DECODER"] = "OFF"
        tc.variables["WITH_AOM_ENCODER"] = "OFF"
        tc.variables["WITH_X265"] = "OFF"
        tc.variables["WITH_RAV1E"] = "OFF"
        tc.variables["WITH_JPEG_DECODER"] = "OFF"
        tc.variables["WITH_JPEG_ENCODER"] = "OFF"
        tc.variables["WITH_OPENJPEG_DECODER"] = "OFF"
        tc.variables["WITH_OPENJPEG_ENCODER"] = "OFF"
        # Disable gdk-pixbuf plugin and tests.
        tc.variables["WITH_GDK_PIXBUF"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # Enable CLI tools (heif-info, heif-dec, heif-enc).
        tc.variables["WITH_EXAMPLES"] = "ON"
        # Reduced visibility causes symbol hiding that breaks static linking
        # on some toolchains; keep it off for aarch64/OHOS.
        tc.variables["WITH_REDUCED_VISIBILITY"] = "OFF"
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
        # The CMake target is "heif" (libheif.a / -lheif).
        self.cpp_info.libs = ["heif"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::heif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
        # C++ runtime (libheif is C++17); libc++ on OHOS/Linux-clang.
        if self.settings.os in ("Linux", "OHOS"):  # R32
            self.cpp_info.system_libs = ["pthread", "c++"]
