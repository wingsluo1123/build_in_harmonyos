#!/usr/bin/env python3
"""Installed-package consumer test for LIVE555."""

import os
import platform

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LiveTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The official CI and the acceptance run execute on HarmonyOS itself.
        # A Linux shadow runner may auto-detect qemu-aarch64 as "can_run" but
        # lacks the OHOS dynamic loader; in that environment compilation is the
        # valid shadow check and runtime remains covered by the native device.
        native_ohos = str(self.settings.os) == "OHOS" and platform.system() == "HarmonyOS"
        native_host = str(self.settings.os) != "OHOS" and can_run(self)
        if native_ohos or native_host:
            exe = os.path.join(self.cpp.build.bindirs[0], "test_live")
            self.run(exe, env="conanrun")
        else:
            self.output.warning(
                "SKIP runtime on non-HarmonyOS shadow host; native HarmonyOS test is required"
            )
