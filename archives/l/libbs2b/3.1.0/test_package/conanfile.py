"""Build and execute a small C consumer of libbs2b's packaged public API."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Libbs2bTestConan(ConanFile):
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
        self.run("./test_libbs2b", cwd=self.build_folder, env="conanrun")
