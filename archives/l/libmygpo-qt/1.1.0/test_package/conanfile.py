import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

class MygpoTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self, generator="Ninja").generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["-j1"])

    def test(self):
        self.run(os.path.join(self.cpp.build.bindir, "test_mygpo"), env="conanrun")
