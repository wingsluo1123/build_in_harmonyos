#!/usr/bin/env python3
"""Conan test_package — dhcpstarv 0.2.3

Tests the dhcpstarv binary. dhcpstarv is a command-line tool (not a library),
so we test the binary directly: running it with --help prints the version and
Usage message and exits 0. The test script verifies the output content.
"""
import os

from conan import ConanFile


class DhcpstarvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for a binary tool

    def test(self):
        bin_dir = self.dependencies["dhcpstarv"].cpp_info.bindirs[0]
        dhcpstarv_bin = os.path.join(bin_dir, "dhcpstarv")
        # 调用 test.sh 验证 dhcpstarv --help 打印版本 0.2.3 且退出码 0
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'bash "{test_script}" "{dhcpstarv_bin}"', env="conanrun")
