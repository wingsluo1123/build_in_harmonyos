#!/usr/bin/env python3
"""Conan test_package for proxycheck 0.49a - consumer verification.

proxycheck 是 application 包（无可链接库 API），R34 口径的消费者测试 = 以使用者身份
执行包内已安装的二进制并按退出码 + 输出断言行为。
"""
import os

from conan import ConanFile


class ProxycheckTestConan(ConanFile):
    """调用已安装的 proxycheck / proxylogger，执行离线确定性断言（smoke.sh，7 项）。"""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # 单一事实源：与 conanfile.py build() 一样用 PATH 解析的 `bash`，不再读 CONFIG_SHELL——
        # 仓库 profile 的 CONFIG_SHELL=/data/service/hnp/bin/bash 在设备上不存在（notes.md 已知限制），
        # 而 build() 从不读该变量；两条执行路径取同一真值。断言数与用例分母不变。
        dep = self.dependencies["proxycheck"]
        man = os.path.join(dep.package_folder, "man")
        # conan 在 test_package 目录内执行 test()，smoke.sh 用相对路径引用。
        self.run(
            f"bash -c 'export PROXYCHECK_MAN=\"{man}\" && bash smoke.sh'",
            env="conanrun",
        )
