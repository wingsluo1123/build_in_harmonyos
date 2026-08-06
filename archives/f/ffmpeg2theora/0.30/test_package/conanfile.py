#!/usr/bin/env python3
"""Conan test_package — ffmpeg2theora 0.30.

R34: Test must execute the packaged binary.
Runs `ffmpeg2theora --help` to verify the binary is functional.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Ffmpeg2TheoraTestConan(ConanFile):
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
        # R34: Execute the packaged binary
        bin_path = os.path.join(self.deps_env_info["ffmpeg2theora"].bindirs[0], "ffmpeg2theora")
        self.run(f'"{bin_path}" --help', env="conanrun")
