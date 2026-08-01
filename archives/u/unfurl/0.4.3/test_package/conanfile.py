#!/usr/bin/env python3
"""Conan test_package for unfurl 0.4.3 — verify the installed executable.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

unfurl is a Go CLI tool; the test verifies the packaged binary exists, is
executable, and produces the exact output documented upstream for each of
its URL-processing modes (see test.sh).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class UnfurlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test.sh", "MANIFEST.yml"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Go CLI 工具, test_package 无 C/C++ 编译步骤;
        # 真实校验在 test() 中通过 test.sh 完成。
        pass

    def _test_script(self):
        for folder in (self.source_folder, self.recipe_folder):
            if not folder:
                continue
            candidate = os.path.join(folder, "test.sh")
            if os.path.isfile(candidate):
                return candidate
        raise ConanException("FAIL: 未找到 test_package/test.sh")

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

        if not can_run(self):
            self.output.warning(
                "交叉编译环境无法执行目标架构二进制, 已跳过运行时功能校验; "
                "产物存在性与可执行位校验已通过")
            return

        # 运行时功能校验: 逐条比对 6 种模式的实际输出与上游 README 官方示例。
        # OHOS 默认 PATH 下未必有 bash, 沿用 profile 提供的 CONFIG_SHELL。
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL")
                 or shutil.which("bash")
                 or "/data/service/hnp/bin/bash")
        script = self._test_script()
        self.run(f'"{shell}" "{script}" "{bin_path}"', env="conanrun")
