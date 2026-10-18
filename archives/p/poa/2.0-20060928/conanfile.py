#!/usr/bin/env python3
"""Conan recipe for POA 2.0-20060928 (CMake; upstream Makefile modules)."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
import os
import shlex
import sys


class PoaConan(ConanFile):
    name = "poa"
    version = "2.0-20060928"
    description = "Partial Order Alignment library and multiple sequence alignment CLI"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/poamsa/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    exports_sources = "test_package/licenses/*", "test_package/cli_regression.py", "test_package/data/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            filename="poa_2.0+20060928.orig.tar.gz", strip_root=True)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # The original Makefile has no check/test target. Run its README
        # example, six downstream Debian scenarios, and additional regressions.
        runner = os.path.join(self.source_folder, "test_package", "cli_regression.py")
        fixtures = os.path.join(self.source_folder, "test_package", "data")
        binary = os.path.join(self.build_folder, "poa")
        output = os.path.join(self.build_folder, "cli-results")
        args = [sys.executable, runner, binary, self.source_folder, fixtures, output]
        self.run(" ".join(shlex.quote(arg) for arg in args))

    def package(self):
        CMake(self).install()
        copy(self, "*", os.path.join(self.source_folder, "test_package", "licenses"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lpo"]
        self.cpp_info.includedirs = ["include/poa"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/poa"]
        self.cpp_info.defines = ["USE_WEIGHTED_LINKS", "USE_PROJECT_HEADER"]
        self.cpp_info.set_property("cmake_file_name", "poa")
        self.cpp_info.set_property("cmake_target_name", "poa::lpo")
        if self.settings.os in ("Linux", "OHOS", "Macos", "FreeBSD"):
            self.cpp_info.system_libs = ["m"]
