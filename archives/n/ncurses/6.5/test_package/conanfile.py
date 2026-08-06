import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NcursesTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Also run the test binary directly for L0d compliance
        # Use cmake layout to find the binary path
        self.run(f"{os.path.join(self.build_folder, 'test_ncurses')}", env="conanrun")
