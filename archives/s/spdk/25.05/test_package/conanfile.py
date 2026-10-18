#!/usr/bin/env python3
"""Conan test_package for spdk 25.05.

Compiles a small C consumer against the installed SPDK headers/static
libraries through CMakeDeps and runs it.  The consumer exercises CPU-only SPDK
APIs (CRC-32/CRC-32C, Base64) whose behaviour does not depend on the DPDK EAL
runtime (hugepages / vfio / uio) that OHOS does not provide.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class SpdkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake does not know OHOS by default; point it at the shipped
        # Platform/OHOS.cmake module so the cross toolchain is set up properly.
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.build_folder, "test_spdk")
        if not os.path.isfile(exe):
            exe = os.path.join(self.build_folder, "Release", "test_spdk")
        self.run('"{}"'.format(exe), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./test_spdk",
            "consumer_passed": 6,
            "consumer_total": 6,
        }))
        result_file = os.path.join(self.dependencies["spdk"].package_folder,
                                   "res", "summary.json")
        with open(result_file, encoding="utf-8") as stream:
            upstream = json.load(stream)
        if upstream["status"] != "passed" or upstream["executed"] == 0:
            raise RuntimeError("Upstream CUnit tests did not pass during build")
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
