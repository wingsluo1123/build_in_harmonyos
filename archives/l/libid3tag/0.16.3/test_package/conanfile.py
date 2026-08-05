import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import can_run

class TestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def layout(self):
        cmake_layout(self)
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(f"{bash} -c './test_package'", env="conanrun")
