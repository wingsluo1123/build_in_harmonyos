#!/usr/bin/env python3
"""test_package for tigervnc 1.15.0 — consumer verification of the RFB core.

Builds a real consumer (test_tigervnc.cxx) against the installed headers and the
exported `tigervnc::rfb` CMake target, then executes it. The test asserts RFB
API behaviour that must hold on OpenHarmony PC: hex codec round-trip (rfb::util),
rectangle arithmetic (rfb::Rect), PixelFormat parsing/validation and exact
8-bit round-trip plus rgb888->rgb565 downconversion, and the VNC-auth DES
primitive (rfb/d3des). No X11, FLTK or PAM is involved.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class TigerVNCTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The test_package is a separate conanfile, so it needs its own
        # CMakeDeps run to produce tigervncConfig.cmake (plus the dependency
        # config files find_dependency pulls in). Without this,
        # find_package(tigervnc) fails outright.
        CMakeDeps(self).generate()
        if self.settings.os == "OHOS":
            # Same HarmonyOS/OHOS platform-module mismatch as the main recipe.
            self.conf_info.define("tools.cmake.cmaketoolchain:system_name", "OHOS")
        tc = CMakeToolchain(self)
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building without an emulator: build verified only")
            return
        # Run the consumer binary directly: it carries the assertions, and the
        # summary lands in the conan create log (CI parses that log for real
        # test evidence). No ctest indirection needed for a single binary.
        binary = os.path.join(self.cpp.build.bindirs[0], "test_tigervnc")
        if not os.path.isfile(binary):
            raise ConanException("consumer test binary not built: %s" % binary)
        self.run('"%s"' % binary, env="conanrun")
