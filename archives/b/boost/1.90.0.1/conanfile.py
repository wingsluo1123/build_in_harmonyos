#!/usr/bin/env python3
"""Conan recipe for Boost 1.90.0.1 compiled components.

The existing boost/1.90.0 archive is intentionally header-only. This revision
adds the compiled Boost libraries needed by downstream packages such as
FastNetMon while keeping the upstream source version at 1.90.0.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir


class BoostCompiledConan(ConanFile):
    name = "boost"
    version = "1.90.0.1"
    description = "Boost C++ Libraries 1.90.0 compiled component subset"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    topics = ("boost", "cpp", "thread", "serialization", "regex")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _components = (
        "atomic",
        "chrono",
        "filesystem",
        "program_options",
        "regex",
        "serialization",
        "thread",
        "timer",
    )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BOOST_INCLUDE_LIBRARIES"] = ";".join(self._components)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE_1_0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]

        for component in self._components:
            info = self.cpp_info.components[component]
            info.set_property("cmake_target_name", f"Boost::{component}")
            info.set_property("cmake_file_name", "Boost")
            info.includedirs = ["include"]
            info.libdirs = ["lib"]
            info.libs = [f"boost_{component}"]

        self.cpp_info.components["chrono"].requires = ["atomic"]
        self.cpp_info.components["thread"].requires = ["chrono", "atomic"]
        self.cpp_info.components["timer"].requires = ["chrono"]

        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.components["thread"].system_libs.append("pthread")
