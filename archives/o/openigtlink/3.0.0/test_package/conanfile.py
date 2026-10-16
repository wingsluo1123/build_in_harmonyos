#!/usr/bin/env python3
"""Conan test_package — openigtlink 3.0.0 (consumer-perspective test).

This is layer 2 of docs/TEST_QUALITY_SPEC.md: CI runs it automatically through
`conan create`.

The test binary is built against the installed package only (the exported CMake
target OpenIGTLink::OpenIGTLink) and verifies that a downstream project can
compile, link and run against it on OpenHarmony / HarmonyOS.

File location: archives/o/openigtlink/3.0.0/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class OpenigtlinkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # The OHOS case of the consumer test performs a task-private directory
        # round trip. TMPDIR is not guaranteed to be exported by the build
        # environment, so point it at a directory owned by this test run - the
        # same "task-private scratch space" contract a HarmonyOS app receives.
        temporary = os.path.join(self.build_folder, "consumer-tmp")
        os.makedirs(temporary, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", temporary)
        environment.define("LC_ALL", "C")
        with environment.vars(self).apply():
            executable = os.path.join(self.cpp.build.bindirs[0], "test_openigtlink")
            self.run(executable, env="conanrun")
