#!/usr/bin/env python3
"""Consumer test for the packaged wavetral command."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class WavetralTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        dep = self.dependencies["wavetral"]
        if not dep.package_folder:
            raise ConanException("wavetral package folder is unavailable")
        exe = os.path.join(dep.package_folder, "bin", "wavetral")
        if not os.path.isfile(exe) or not os.access(exe, os.X_OK):
            raise ConanException(f"missing packaged command: {exe}")
        tc = CMakeToolchain(self)
        tc.variables["WAVETRAL_BIN"] = exe.replace("\\", "/")
        tc.generate()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("SKIP: cross-built wavetral cannot run on this host")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_wavetral")
        self.run(exe, env="conanrun")
