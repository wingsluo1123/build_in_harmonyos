#!/usr/bin/env python3
"""Conan test_package for iperf 2.2.1 — binary tool smoke test.

Verifies that the iperf binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class IperfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the iperf binary in the package
        bin_path = os.path.join(self.dependencies["iperf"].package_folder, "bin", "iperf")
        if not os.path.exists(bin_path):
            # Try alternate path
            for root, dirs, files in os.walk(self.dependencies["iperf"].package_folder):
                if "iperf" in files:
                    bin_path = os.path.join(root, "iperf")
                    break
        self.run(f'"{bin_path}" --version', env="conanrun")
