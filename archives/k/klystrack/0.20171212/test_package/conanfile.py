#!/usr/bin/env python3
"""Consumer test for klystrack 0.20171212 — verify binary works."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy


class KlystrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy test source to build folder
        copy(self, "test.c", src=self.source_folder, dst=self.build_folder)

    def generate(self):
        # aireview P1: CMakeLists.txt 补 SDL2 find_package + target_link_libraries（避链接炸）
        # aireview P2: CC 硬编码 → CMake 用 CMAKE_C_COMPILER 从环境取
        with open(os.path.join(self.build_folder, "CMakeLists.txt"), "w") as f:
            f.write("""cmake_minimum_required(VERSION 3.5)
project(test_klystrack C)
find_package(SDL2 REQUIRED)
add_executable(test_klystrack test.c)
target_link_libraries(test_klystrack PRIVATE SDL2::SDL2)
""")

    def test(self):
        # Build and run test binary
        self.run("cmake . -DCMAKE_BUILD_TYPE=Release", cwd=self.build_folder)
        self.run("cmake --build . --config Release", cwd=self.build_folder)
        if can_run(self):
            # Medium: env="conanrun" + VirtualRunEnv 自动注入 PATH（aireview: 标准运行时环境）
            self.run("./test_klystrack", cwd=self.build_folder, env="conanrun")