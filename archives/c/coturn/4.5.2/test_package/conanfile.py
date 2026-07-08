#!/usr/bin/env python3
"""Conan test_package — coturn 4.5.2 consumer L1 test.

Verifies that libturnclient can be linked and its STUN/TURN message API
called correctly (BINDING/ALLOCATE request creation + validation).
Also runs the upstream RFC 5769 compliance test binary from the package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CoturnTestConan(ConanFile):
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
        # Consumer test: links against libturnclient and calls STUN API
        self.run("./test_coturn", env="conanrun")

        # Run upstream RFC 5769 compliance test binary from the installed package
        coturn_pkg = self.dependencies["coturn"].package_folder
        rfc5769check = os.path.join(coturn_pkg, "bin", "turnutils_rfc5769check")
        if os.path.isfile(rfc5769check):
            self.run(f"{rfc5769check}", env="conanrun")
