#!/usr/bin/env python3
"""test_package conanfile for dhcpd-pools 3.2.

Offline smoke test: runs dhcpd-pools binary with fixed test data
to verify parsing, output formats, and error handling.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building
from conan.tools.files import copy


class DhcpdpoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Copy test data next to the binary for offline smoke test
        src_dir = os.path.join(self.source_folder, "..", "test_package")
        for f in ("dhcpd.conf", "dhcpd.leases"):
            copy(self, f, src_dir, self.build_folder)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        # The dhcpd-pools binary is available via the dependency's bindirs
        dhcpd_pools_path = os.path.join(self.dependencies["dhcpd-pools"].cpp_info.bindirs[0], "dhcpd-pools")
        self.output.info(f"dhcpd-pools binary: {dhcpd_pools_path}")
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_dhcpd-pools")
        self.run(f"cd {self.build_folder} && {bin_path} {dhcpd_pools_path}", env="conanrun")
