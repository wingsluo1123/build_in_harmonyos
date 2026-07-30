#!/usr/bin/env python3
"""Conan test_package for lv2 — Conan L1 official test (consumer side).

CI runs this automatically via `conan create` (which invokes test_package).
File location: archives/l/lv2/<version>/test_package/conanfile.py
"""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.errors import ConanInvalidConfiguration


class Lv2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lv2 test supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("ctest --output-on-failure", cwd=self.build_folder)
