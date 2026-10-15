from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PlankTestConan(ConanFile):
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
        import os
        exe = os.path.join(self.build_folder, "test_plank")
        self.run(exe, env="conanrun")
