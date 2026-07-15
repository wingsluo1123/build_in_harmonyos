#!/usr/bin/env python3
"""Conan test_package for ipcalc — verifies the binary works correctly.

Tests that ipcalc can:
1. Show version
2. Calculate IPv4 network info
3. Calculate IPv6 network info
"""
import os

from conan import ConanFile


class IpcalcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        # Find ipcalc binary in the package
        pkg = self.dependencies["ipcalc"]
        bin_path = None
        for bindir in pkg.cpp_info.bindirs:
            candidate = os.path.join(bindir, "ipcalc")
            if os.path.exists(candidate):
                bin_path = candidate
                break

        assert bin_path is not None, "ipcalc binary not found in package"

        # Test 1: Version output
        self.run(f'"{bin_path}" --version', env="conanrun")

        # Test 2: IPv4 calculation — must show network and broadcast
        self.run(f'"{bin_path}" 192.168.1.1/24 | grep "192.168.1.0/24"', env="conanrun")
        self.run(f'"{bin_path}" 192.168.1.1/24 | grep "192.168.1.255"', env="conanrun")

        # Test 3: IPv6 calculation
        self.run(f'"{bin_path}" 2001:db8::/32 | grep "2001:db8::"', env="conanrun")
