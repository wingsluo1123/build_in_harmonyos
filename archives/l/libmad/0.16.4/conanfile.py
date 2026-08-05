#!/usr/bin/env python3
"""Conan recipe for libmad 0.16.4 - MPEG audio decoder library (CMake).

libmad is a high-quality MPEG audio decoder library using 100% fixed-point
(integer) computation. This is the Tenacity Team fork which uses CMake.
No external dependencies.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibmadConan(ConanFile):
    name = "libmad"
    version = "0.16.4"
    description = "MPEG audio decoder library"
    license = "GPL-2.0-or-later"
    homepage = "https://codeberg.org/tenacityteam/libmad"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "ASO": [True, False]}
    default_options = {"shared": True, "fPIC": True, "ASO": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libmad requires a POSIX C target")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["ASO"] = self.options.ASO
        tc.cache_variables["EXAMPLE"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mad"]
        self.cpp_info.set_property("cmake_file_name", "mad")
        self.cpp_info.set_property("cmake_target_name", "mad::mad")
        self.cpp_info.set_property("pkg_config_name", "mad")
