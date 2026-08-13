#!/usr/bin/env python3
"""CMake consumer test for Qt TextToSpeech 6.11.1."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtTextToSpeechTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # E225: 用 Conan 管理的唯一临时目录作为 test_package 构建根，
        # 避免 CMakeToolchain 把 CMakeUserPresets.json 写回 source。
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        # E225: 从生成源头阻止 preset 写回 source（user_presets_path=False）。
        tc.user_presets_path = False
        qtbase = self.dependencies["qtbase"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        qttexttospeech = self.dependencies["qttexttospeech"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        # Qt6TextToSpeechConfig.cmake 内部 find_package(Qt6Multimedia REQUIRED)，
        # 必须显式提供 Qt6Multimedia_DIR（qttexttospeech 依赖 qtmultimedia）。
        tc.variables["Qt6Multimedia_DIR"] = os.path.join(
            qtmultimedia, "lib", "cmake", "Qt6Multimedia"
        )
        tc.variables["Qt6TextToSpeech_DIR"] = os.path.join(
            qttexttospeech, "lib", "cmake", "Qt6TextToSpeech"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindirs = self.cpp.build.bindirs
            if not bindirs:
                raise ConanInvalidConfiguration(
                    "qttexttospeech test package has no build bindir"
                )
            executable = os.path.join(bindirs[0], "test_package")
            self.run(executable, env="conanrun", ignore_errors=False)
