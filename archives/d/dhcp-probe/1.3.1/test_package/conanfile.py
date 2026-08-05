#!/usr/bin/env python3
"""Conan test_package for dhcp-probe — verifies the binary works.

Runs `dhcp_probe -v` to check the binary is functional.
Per R34: test must exercise the actual package (not a stub).
"""
import os

from conan import ConanFile


class DhcpProbeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: verify the binary actually works
        bin_dir = self.dependencies["dhcp-probe"].cpp_info.bindirs[0]
        bin_path = os.path.join(bin_dir, "dhcp_probe")
        self.run(f'"{bin_path}" -v', env="conanrun")
