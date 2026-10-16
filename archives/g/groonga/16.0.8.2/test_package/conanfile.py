import os
import sys
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout

class GroongaTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    test_type = "explicit"
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
        if cross_building(self):
            raise ConanInvalidConfiguration("Native Groonga runtime validation is required")
        pkg = self.dependencies["groonga"].package_folder
        self.run('"%s" "%s" "%s" "%s" "%s" "%s"' % (
            sys.executable, os.path.join(self.source_folder, "test_groonga_runtime.py"),
            pkg, self.build_folder, self.source_folder, str(self.settings.os)), env="conanrun")
