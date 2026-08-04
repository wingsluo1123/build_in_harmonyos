#!/usr/bin/env python3
"""Conan recipe for aircrack-ng 1.7 on HarmonyOS.

aircrack-ng is a WiFi security assessment tool suite. This recipe
builds the core tools (aircrack-ng, kstats, makeivs-ng) using a
custom CMake build since the upstream autotools requires automake
which is not available on OHOS.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AircrackngConan(ConanFile):
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)
    name = "aircrack-ng"
    version = "1.7"
    description = "WiFi security assessment tool suite (aircrack-ng, kstats, makeivs-ng)"
    license = "GPL-2.0-or-later"
    homepage = "https://aircrack-ng.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # Apply patches (if any declared in conandata.yml)
        apply_conandata_patches(self)
        # Copy CMakeLists.txt to source (upstream uses autotools, we use CMake)
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
