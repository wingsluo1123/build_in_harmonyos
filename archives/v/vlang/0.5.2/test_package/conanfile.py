#!/usr/bin/env python3
"""Conan test package for vlang/0.5.2."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class VTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def export_sources(self):
        copy(self, "test_v_language.v", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "test_v_metadata.cpp", src=self.recipe_folder, dst=self.export_sources_folder)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder)

        if not can_run(self):
            self.output.info("Skipping runtime test because target binaries cannot run here")
            return

        package_folder = self.dependencies["vlang"].package_folder
        is_windows = str(self.settings.os) == "Windows"
        v_exe = os.path.join(package_folder, "bin", "v.bat" if is_windows else "v")
        vmodules = os.path.join(self.build_folder, "vmodules")
        os.makedirs(vmodules, exist_ok=True)
        os.environ["VMODULES"] = vmodules
        test_src = os.path.join(self.source_folder, "test_v_language.v")
        test_bin = os.path.join(self.build_folder, "test_v_language")
        test_cmd = f"{test_bin}.exe" if is_windows else test_bin

        self.run(f'"{v_exe}" version', env="conanrun")
        self.run(f'"{v_exe}" -o "{test_bin}" "{test_src}"', env="conanrun")
        self.run(f'"{test_cmd}"', env="conanrun")
