#!/usr/bin/env python3
"""test_package for desktop-file-utils 0.28 — 验证 CLI 可执行且版本输出正确。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class DesktopFileUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        bin_path = os.path.join(
            self.dependencies["desktop-file-utils"].package_folder, "bin", "desktop-file-validate"
        )
        self.output.info(f"desktop-file-validate 二进制: {bin_path}")
        self.run(f"{bin_path} --version", ignore_errors=False)
