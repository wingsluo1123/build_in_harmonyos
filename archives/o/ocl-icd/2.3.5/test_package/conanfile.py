#!/usr/bin/env python3
"""Conan test_package — ocl-icd 2.3.5

Runs the installed loader with no vendors and a controlled vendor ICD.
Checks loader identity, API error handling, and platform dispatch.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OclIcdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # CL headers for the consumer test; the ocl-icd package itself
        # builds against its bundled khronos-headers copy.
        self.requires("opencl-headers/2026.05.29")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0],
                                    "test_ocl_icd")
            self.run(bin_path + " empty", env="conanrun")
            self.run(bin_path + " fixture", env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": bin_path + " empty && " + bin_path + " fixture",
                "discovered": 2,
                "passedCount": 2,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(marker))
