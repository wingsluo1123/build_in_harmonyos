#!/usr/bin/env python3
"""test_package for oarc-dsc — 以真实消费者方式验证已安装的包。

包内只有 bin/dsc（CLI 应用，无库、无头文件），因此验证方式是执行二进制：test.sh
用包内 dsc 回放一个自造 pcap 并校验 JSON 统计结果（完整消费者用例），覆盖上游
src/test 源码树内测试无法覆盖的「已安装产物是否可用」。
"""
import os

from conan import ConanFile


class OarcDscTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh(mksh) 直接执行 ELF 有限制，用 bash 包一层（同 2048.c）
        bash = os.environ.get("CONFIG_SHELL")
        if not bash:
            candidate = "/data/service/hnp/bin/bash"
            bash = candidate if os.path.exists(candidate) else "bash"
        self.run(f"{bash} test.sh", env="conanrun")
