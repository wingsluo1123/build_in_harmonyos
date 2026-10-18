#!/usr/bin/env python3
"""test_package for pmidi 1.7.1 — L1 消费者测试。

R34：真实执行被测包安装的 pmidi 二进制（非空壳），并叠加一个鸿蒙特有测试。
"""
from conan import ConanFile


class PmidiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34：真实运行被测包产出的可执行文件
        self.run("sh test.sh", env="conanrun")
        # 鸿蒙特有测试：OHOS 平台不变量（ELF64/AArch64、.codesign、musl loader、依赖闭包）
        self.run("sh test_ohos.sh", env="conanrun")
