import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LxctemplateslegacyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # Run test_main to verify installed template files from the package
        pkg_folder = self.dependencies["lxc-templates-legacy"].package_folder
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_main")
        self.run(f"{bin_path} {pkg_folder}", env="conanrun")
