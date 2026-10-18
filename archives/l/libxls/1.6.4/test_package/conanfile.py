import os
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
        package = Path(self.dependencies["libxls"].package_folder)
        binary = package / "bin/xls2csv"
        libraries = list((package / "lib").glob("libxlsreader.*"))
        if not binary.is_file() or not libraries:
            raise RuntimeError("Installed libxls library/CLI missing")
        fixture_root = Path(self.build_folder) / "fixtures"
        self.run(shlex.join([sys.executable, str(Path(self.source_folder) / "fixture.py"),
                             str(Path(self.source_folder)), str(fixture_root)]), env="conanrun")
        fixture = fixture_root / "test2.xls"
        if can_run(self):
            self.run(shlex.join([str(Path(self.build_folder) / self.cpp.build.bindirs[0] / "consumer"),
                                 str(fixture)]), env="conanrun")
            self.run(shlex.join([sys.executable, str(Path(self.source_folder) / "test_cli.py"),
                                 str(binary), str(fixture),
                                 str(Path(self.build_folder) / "harmony-e2e")]), env="conanrun")
