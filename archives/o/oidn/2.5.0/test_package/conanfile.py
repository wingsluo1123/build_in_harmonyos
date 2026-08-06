import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestOidnConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run(os.path.join(cmake.test_output_folder, "test_oidn"), env="conanrun")
