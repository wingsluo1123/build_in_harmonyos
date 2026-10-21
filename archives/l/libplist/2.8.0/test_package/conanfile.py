from pathlib import Path
import shlex
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

class Consumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = Path(self.dependencies["libplist"].package_folder)
        binary = package / "bin/plistutil"
        if not binary.is_file() or not list((package / "lib").glob("libplist-2.0.*")):
            raise RuntimeError("Installed libplist library/CLI missing")
        if can_run(self):
            self.run(shlex.join([str(Path(self.build_folder) / self.cpp.build.bindirs[0] / "consumer")]), env="conanrun")
            self.run(shlex.join([sys.executable, str(Path(self.source_folder) / "test_cli.py"),
                                 str(binary), str(Path(self.build_folder) / "harmony-e2e")]), env="conanrun")
