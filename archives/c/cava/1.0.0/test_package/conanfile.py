#!/usr/bin/env python3
"""test_package for cava 1.0.0 — 以真实使用者身份调用已安装的 `cava` 二进制。

cava 是应用程序（不对外链接库），消费者验证的正确形态是**执行被测二进制 +
对可观测行为做断言**（与已合入的 2048.c 1.0.3 同款）：test.sh 逐项检查
`-v/--version` 输出、`-h/--help` 契约、未知选项的非零退出码，
任何一项不符即非零退出（真实决定退出码，不是只打印）。
"""
import os

from conan import ConanFile


class CavaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 无法执行 ELF 二进制，用 bash 包一层
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = "/bin/sh"
        self.run(f"{bash} test.sh", env="conanrun")
