import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BlenderTestConan(ConanFile):
    """test_package for blender - verifies the headless build works"""
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
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
        # Run the basic Blender executable in headless mode
        # --version should work without GUI
        self.run("blender --version", env="conanrun")
