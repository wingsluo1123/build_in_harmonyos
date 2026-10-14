#!/usr/bin/env python3
"""test_package — 消费者视角验证已安装的 unudhcpd 二进制（层2）

unudhcpd 的产物是可执行文件，消费者验证方式 = 以真实用户的方式调用它：
执行 test.sh，断言 -v / 无参数 / 服务启动路径三条可观测行为。
"""
import os

from conan import ConanFile


class UnudhcpdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /bin/sh 为 Toybox shell，执行 ELF 二进制受限；
        # 与 2048.c / account-utils 同先例，用 bash 包裹执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
