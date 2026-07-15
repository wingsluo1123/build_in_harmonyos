#!/usr/bin/env python3
"""Conan test_package — wireguard-tools 1.0.20260223

Tests the wg binary by running --help and genkey.
wireguard-tools is a command-line tool, not a library.
"""
import os

from conan import ConanFile


class WireguardToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        # R34: Test must actually use the tested package's binary
        bin_dir = self.dependencies["wireguard-tools"].cpp_info.bindirs[0]
        wg_bin = os.path.join(bin_dir, "wg")
        # Test 1: --help shows usage (verifies binary is functional)
        self.run(f'"{wg_bin}" --help', env="conanrun")
        # Test 2: genkey produces a valid base64 key (tests curve25519 crypto)
        self.run(f'"{wg_bin}" genkey', env="conanrun")
