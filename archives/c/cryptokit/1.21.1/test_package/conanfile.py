import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run

class CryptokitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # R34: Actually compile test.c that calls SHA-256 API
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: Actually run the compiled test binary
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_cryptokit")
            self.run(bin_path, env="conanrun")
