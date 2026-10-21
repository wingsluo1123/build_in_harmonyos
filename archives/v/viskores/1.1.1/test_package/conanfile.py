#!/usr/bin/env python3
"""Exercise the installed Viskores component graph and library functions."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ViskoresTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self, generator="Ninja")
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = "Linux"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self.run("cmake --build . --parallel 1", env="conanbuild")

    def test(self):
        self.run("ctest --no-tests=error --output-on-failure --verbose --timeout 120 "
                 "--output-junit consumer-tests.xml", env="conanrun")
