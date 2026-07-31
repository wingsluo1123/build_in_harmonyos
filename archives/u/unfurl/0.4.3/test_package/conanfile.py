#!/usr/bin/env python3
"""Conan test_package for unfurl 0.4.3 — verify the installed executable.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

unfurl is a Go CLI tool; the test verifies the packaged binary exists and
actually processes a URL from stdin (modes: -u unique, domains).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class UnfurlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Go CLI 工具, 无 C/C++ 编译步骤
        pass

    def test(self):
        if can_run(self):
            # 验证二进制存在且可执行
            bin_path = os.path.join(self.dependencies["unfurl"].package_folder,
                                    "bin", "unfurl")
            if not os.path.isfile(bin_path):
                raise SystemExit(f"FAIL: {bin_path} 不存在")
            if not os.access(bin_path, os.X_OK):
                raise SystemExit(f"FAIL: {bin_path} 不可执行")

            # 实际运行: 从 stdin 喂 URL, 提取域名
            self.run(
                f'echo "https://example.com/foo?a=b" | {bin_path} -u domains',
                env="conanrun")
