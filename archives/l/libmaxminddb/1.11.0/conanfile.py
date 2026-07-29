#!/usr/bin/env python3
"""Conan recipe for libmaxminddb 1.11.0."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir


class LibmaxminddbConan(ConanFile):
    name = "libmaxminddb"
    version = "1.11.0"
    description = "C library for the MaxMind DB file format"
    license = "Apache-2.0"
    homepage = "https://maxmind.github.io/libmaxminddb/"
    url = "https://github.com/maxmind/libmaxminddb"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_TESTING"] = False
        toolchain.variables["MAXMINDDB_BUILD_BINARIES"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["maxminddb"]
        self.cpp_info.set_property("cmake_file_name", "maxminddb")
        self.cpp_info.set_property("cmake_target_name", "maxminddb::maxminddb")
        self.cpp_info.set_property("pkg_config_name", "libmaxminddb")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32"]
