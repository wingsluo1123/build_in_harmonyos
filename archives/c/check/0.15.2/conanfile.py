#!/usr/bin/env python3
"""Conan recipe for Check 0.15.2."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class CheckConan(ConanFile):
    name = "check"
    version = "0.15.2"
    description = "Unit testing framework for C"
    license = "LGPL-2.1-or-later"
    homepage = "https://libcheck.github.io/check/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("check supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CHECK_ENABLE_TESTS"] = False
        tc.variables["CHECK_ENABLE_TIMEOUT_TESTS"] = False
        tc.variables["ENABLE_MEMORY_LEAKING_TESTS"] = False
        tc.variables["CHECK_ENABLE_GCOV"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["check"]
        system_libs = ["m", "pthread"]
        if str(self.settings.os) != "OHOS":
            system_libs.append("rt")
        self.cpp_info.system_libs = system_libs
        self.cpp_info.set_property("cmake_file_name", "Check")
        self.cpp_info.set_property("cmake_target_name", "Check::Check")
        self.cpp_info.set_property("pkg_config_name", "check")
