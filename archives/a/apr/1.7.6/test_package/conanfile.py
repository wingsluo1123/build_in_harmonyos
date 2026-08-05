import os
from conan import ConanFile
from conan.tools.cmake import CMake


class AprTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_exe = os.path.join(self.build_folder, "test_package")
        self.run(test_exe, env="conanrun")
