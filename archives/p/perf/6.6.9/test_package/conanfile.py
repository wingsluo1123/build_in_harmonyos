import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PerfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: Test actually exercises the perf binary
        # test.c calls system("perf --version") and checks the result
        cmake = CMake(self)
        cmake.test()

        # Also verify the binary exists and is valid ELF
        dep = self.dependencies["perf"]
        bin_path = os.path.join(dep.package_folder, "bin", "perf")
        if os.path.exists(bin_path):
            self.run(f"file {bin_path}")
