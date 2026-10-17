#!/usr/bin/env python3
"""Consumer test for totem-pl-parser 3.26.7.

Builds a real client that links the packaged library, parses a playlist
through the public API and validates the parsed entries.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class TotemPlParserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The binary has no RUNPATH (the OHOS loader ignores $ORIGIN here), so
        # it must run with the run environment of the dependency closure.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_totem-pl-parser")
        self.run(bin_path, env="conanrun")
