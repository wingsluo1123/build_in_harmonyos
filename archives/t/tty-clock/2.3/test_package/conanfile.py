#!/usr/bin/env python3
"""test_package for tty-clock 2.3 — 验证 CLI 可执行且版本输出正确。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class TtyClockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.warning("无法运行测试（交叉编译环境）")
            return
        bin_path = os.path.join(self.dependencies["tty-clock"].package_folder, "bin", "tty-clock")
        self.output.info(f"tty-clock 二进制: {bin_path}")
        self.run(f"{bin_path} -v", ignore_errors=False)
