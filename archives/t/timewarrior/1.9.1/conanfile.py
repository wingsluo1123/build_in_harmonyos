#!/usr/bin/env python3
"""Conan recipe for Timewarrior 1.9.1."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class TimewarriorConan(ConanFile):
    name = "timewarrior"
    version = "1.9.1"
    description = "Command-line time tracking application"
    license = "MIT"
    homepage = "https://timewarrior.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Timewarrior supports Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "cmake", "CXXSniffer.cmake"),
            '${CMAKE_SYSTEM_NAME} MATCHES "Linux"',
            '${CMAKE_SYSTEM_NAME} MATCHES "Linux|HarmonyOS"',
        )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_source = os.path.join(self.source_folder, "test")
            test_build = os.path.join(self.build_folder, "test")
            copy(self, "*.t", src=test_source, dst=test_build)
            for directory in ("basetest", "simpletap", "test_extensions"):
                copy(
                    self,
                    "*",
                    src=os.path.join(test_source, directory),
                    dst=os.path.join(test_build, directory),
                )
            for helper in ("bash_tap.sh", "bash_tap_ti.sh", "timemachine"):
                copy(self, helper, src=test_source, dst=test_build)
            self.run("chmod +x *.t run_all problems", cwd=test_build)
            cmake.build(target="test")
            self.run("./AtomicFileTest", cwd=test_build)

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
