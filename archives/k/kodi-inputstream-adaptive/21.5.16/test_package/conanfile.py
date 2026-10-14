#!/usr/bin/env python3
"""Conan test_package for kodi-inputstream-adaptive 21.5.16.

Consumer-side check: compiles a small client against the built
inputstream.adaptive add-on module (CMakeDeps target), then runs it on the
host. The client exercises the C entry points exported by the ADDONCREATOR
macro (kodi/AddonBase.h), a real instance declaration through the stable C
ABI factory, and the OHOS adaptation points of this port (relative DT_SONAME
registration, on-device runtime mapping, self-contained dlopen closure, musl
libc semantics used by the production code). The upstream gtest suite runs
for real inside the package build() (ctest, 58 cases).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KodiInputstreamAdaptiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built inputstream.adaptive consumer cannot run on this host")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_inputstream_adaptive")
        self.run(test_bin, env="conanrun")
