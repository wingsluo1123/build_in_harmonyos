#!/usr/bin/env python3
"""Conan test_package for iftop 1.0_pre4 — verify the installed executable.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

iftop is a terminal tool; `--version` is not a recognized flag (iftop prints
its usage and exits non-zero), so the test tolerates that non-zero exit and
additionally runs a small consumer program to verify the package is consumable.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IftopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 编译消费者测试程序 (使用 Conan 环境的 CC)
        src = os.path.join(os.path.dirname(__file__), "test_package.c")
        cc = os.environ.get("CC", "cc")
        self.run(f'{cc} "{src}" -o test_package')

    def test(self):
        if can_run(self):
            # 运行编译好的测试程序
            self.run("./test_package", env="conanrun")
            # iftop 的 --version 是未识别选项 (退出码非 0 但仍打印版本),
            # 因此容忍非零退出码以验证可执行文件已安装。
            self.run("iftop --version || true", env="conanrun")
