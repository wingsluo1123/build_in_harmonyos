#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CascadeCompilerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self.run(
            'cmake --build "{}" --parallel 2'.format(self.build_folder),
            env="conanbuild",
        )

    def test(self):
        executable = self.cpp.build.bindirs[0] + "/test_cascade"
        cascade_tmp_dir = os.path.join(self.build_folder, "_cascade_tmp")
        os.makedirs(cascade_tmp_dir, exist_ok=True)
        self.run(
            'CASCADE_TMP_DIR="{}" "{}"'.format(cascade_tmp_dir, executable),
            env="conanrun",
        )
