#!/usr/bin/env python3
"""Conan recipe for Imath 3.2.2 (CMake build system).

Imath is a C++ math library developed by the Academy Software Foundation.
It provides 2D/3D vectors, matrices, color types, half-precision floats,
and other numerical types used in computer graphics (notably as the
foundation math library for OpenEXR).

Build system: CMake
Library output: libImath-3_2.so (shared library, default)
Dependencies: none (standalone math library)
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class ImathConan(ConanFile):
    name = "imath"
    version = "3.2.2"
    description = "C++ math library for computer graphics (vectors, matrices, color, half)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/AcademySoftwareFoundation/Imath"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["Imath-3_2"]
        # Include both include/ and include/Imath/ so that both
        # <Imath/ImathVec.h> and <ImathConfig.h> style includes work
        self.cpp_info.includedirs = ["include", "include/Imath"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "Imath")
        self.cpp_info.set_property("cmake_target_name", "Imath::Imath")
