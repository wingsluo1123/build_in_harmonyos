"""Conan test_package for qt-percona-server homebrew - Conan L1 official test.

Uses CMake to build the test binary (CMakeLists.txt handles Qt6::Core/Qt6::Sql linkage).
CI runs this automatically via `conan create` (which invokes test_package).

OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so use bash to wrap.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QtPerconaServerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_driver'", env="conanrun")
