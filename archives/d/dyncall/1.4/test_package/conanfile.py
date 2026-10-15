import sys
from pathlib import Path
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class DyncallTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = Path(self.build_folder, "bin", "consumer")
        if not binary.is_file(): raise RuntimeError("Missing package consumer")
        if can_run(self):
            self.run('"{}" "{}" "{}"'.format(sys.executable, Path(self.source_folder, "run_consumer.py"), binary), env="conanrun")
