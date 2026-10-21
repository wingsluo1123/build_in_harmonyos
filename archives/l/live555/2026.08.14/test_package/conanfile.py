"""Build and execute a small C++ consumer of the packaged LIVE555 libraries."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Live555TestConan(ConanFile):
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
        self.run("./test_live555", cwd=self.build_folder, env="conanrun")
