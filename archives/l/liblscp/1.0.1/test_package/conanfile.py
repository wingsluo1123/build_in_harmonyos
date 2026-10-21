import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LiblscpTestConan(ConanFile):
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
        # Real execution of a consumer binary that links liblscp and asserts
        # library behaviour (exit code decides).  See test_liblscp.c.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_liblscp")
        self.run(exe, env="conanrun")
