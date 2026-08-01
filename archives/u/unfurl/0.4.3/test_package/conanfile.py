#!/usr/bin/env python3
"""Conan test_package for unfurl 0.4.3 — verify the installed executable.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

unfurl is a Go CLI tool; the test verifies the packaged binary exists and
actually processes a URL from stdin (modes: -u unique, domains).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
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
        # 产物校验: 纯文件系统检查, 与能否执行目标架构二进制无关,
        # 因此必须无条件执行 —— 交叉编译时这是唯一能守住的底线,
        # 若放进 can_run() 守卫内, test() 在 CI 上将退化为空壳测试。
        bin_path = os.path.join(self.dependencies["unfurl"].package_folder,
                                "bin", "unfurl")
        if not os.path.isfile(bin_path):
            raise ConanException(f"FAIL: 包内未找到可执行文件 {bin_path}")
        if not os.access(bin_path, os.X_OK):
            raise ConanException(f"FAIL: {bin_path} 缺少可执行权限")

        # 运行时功能校验: 从 stdin 喂 URL 提取域名, 仅在可执行目标架构时进行
        if can_run(self):
            self.run(
                f'echo "https://example.com/foo?a=b" | {bin_path} -u domains',
                env="conanrun")
        else:
            self.output.warning(
                "交叉编译环境无法执行 OHOS aarch64 二进制, 已跳过运行时功能校验; "
                "产物存在性与可执行位校验已通过")
