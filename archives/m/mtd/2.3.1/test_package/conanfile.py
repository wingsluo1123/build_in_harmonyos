#!/usr/bin/env python3
"""Conan test_package for mtd (mtd-utils) — L1 smoke test.

R34: 实质调用被测包二进制。mtd 为命令行工具集(纯 application), 无库 API,
因此测试直接运行打包后的核心工具 (mtdinfo/flash_erase/ubiformat 等) 验证
可执行性与版本输出, 禁止空壳测试。
"""
import os

from conan import ConanFile


class MtdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["mtd"].package_folder
        sbin_dir = os.path.join(pkg_folder, "sbin")
        if not os.path.isdir(sbin_dir):
            # 部分 install 布局可能落 bin/
            sbin_dir = os.path.join(pkg_folder, "bin")
        self.run(f"sh test_mtd.sh {sbin_dir}", env="conanrun")
        self.output.info("mtd (mtd-utils) smoke test: OK")