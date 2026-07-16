#!/usr/bin/env python3
"""Conan recipe — libogg 1.3.6 (CMake).

R26: libogg is a system-name-colliding library — build static only
     to avoid polluting /lib, /lib64 with a shared libogg.so.
     Uses CMake to avoid E165 shebang issues with autotools configure.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class LiboggConan(ConanFile):
    name = "libogg"
    version = "1.3.6"
    description = "Ogg multimedia container library"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name-colliding library — BUILD_SHARED_LIBS=OFF
        tc.variables["BUILD_SHARED_LIBS"] = False
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
        self.cpp_info.libs = ["ogg"]
        self.cpp_info.set_property("cmake_file_name", "libogg")
        self.cpp_info.set_property("cmake_target_name", "libogg::libogg")
