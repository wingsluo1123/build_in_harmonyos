#!/usr/bin/env python3
"""Conan test_package for iw 6.17 — 消费者视角真实验证。

上游注册自动化测试用例数 = 0（R51 六探针全 0 命中，见 MANIFEST.yml），Makefile
里唯一的 `check:` 目标是 `sparse -Wall cgcc` 静态分析 lint，**不是测试套件**，
故不作为上游套件执行、也不计入通过率；真实断言全部由本 test_package 承担
（与 fuse 2.9.9 / fstobdf 1.0.8 / esmtp 1.2 同口径）。
"""
from conan import ConanFile


class IwTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本与配方同目录（即归档 test_package/ 目录）——直接驱动已安装的
        # 二进制，不做 copy（避免 test_package/test_package 嵌套污染）。
        pkg_folder = self.dependencies["iw"].package_folder
        self.run('python3 test_iw.py "%s"' % pkg_folder, env="conanrun")
