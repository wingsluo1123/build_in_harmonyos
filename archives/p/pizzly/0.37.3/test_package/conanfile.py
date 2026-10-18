#!/usr/bin/env python3
"""Conan test_package for pizzly 0.37.3 —— 消费者端到端验证。

被测对象是本次 conan 包安装后的 `bin/pizzly` 可执行文件（消费者视角），
不使用源码构建目录产物。实际断言逻辑在 test_pizzly.sh 中（含两个 E2E 用例）。
"""
import os

from conan import ConanFile


class PizzlyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS 的 /system/bin/sh (mksh) 不能执行 ELF，用 bash 承载脚本执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_pizzly.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
