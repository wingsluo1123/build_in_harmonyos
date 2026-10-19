#!/usr/bin/env python3
"""Installed-package tests for xkbcomp 1.4.7.1.

真实执行被测二进制的消费者断言放在同目录的 test_xkbcomp.py（CI 的 L0c 要求
test_package/ 下有独立测试源文件），本文件只负责挂载运行环境并调用它：
conanrun 环境（LD_LIBRARY_PATH 指向 libx11/libxkbfile 等）由 VirtualRunEnv
生成——OHOS loader 忽略 DT_RUNPATH，缺了它被测二进制连加载都做不到。
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XkbcompTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("xkbcomp target host is not runnable")

        script = os.path.join(os.path.dirname(__file__), "test_xkbcomp.py")
        # Conan 沙箱 PATH 里没有 python3 —— 用绝对路径。
        py = "/data/service/hnp/bin/python3" if os.path.isfile(
            "/data/service/hnp/bin/python3"
        ) else sys.executable
        # 断言绑定产物：脚本以 package_folder 为输入，产物被移走时第一步即失败
        # （CI 的破坏性反向验证 R34/L1e 依赖这一点）。
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        self.run(
            f'"{py}" "{script}" "{package_folder}" '
            f'"{self.tested_reference_str}" "{self.settings.os}"',
            env="conanrun",
        )
