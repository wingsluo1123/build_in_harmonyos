#!/usr/bin/env python3
"""Conan test_package for xd 5.00.03 —— 运行真实安装产物 bin/xd。

R34: 端到端调用真实二进制（目录展开 + 配置解析 + 退出码语义），不是打印桩。
HMBS_TEST_PACKAGE_RESULT 门禁标记由 test_xd.sh 输出。
"""
import os
import shutil

from conan import ConanFile


class XdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 真机可能同时存在 hnp bash 与 /bin/sh：按可用性探测，避免
        # profile 的 CONFIG_SHELL 指向不存在的路径。
        candidates = [
            os.environ.get("CONFIG_SHELL", ""),
            os.environ.get("SHELL", ""),
            "/bin/sh",
            "/data/service/hnp/bin/bash",
        ]
        sh = next(
            (s for s in candidates
             if s and os.path.isfile(s) and os.access(s, os.X_OK)),
            shutil.which("sh") or "/bin/sh",
        )
        self.run(f"{sh} test_xd.sh", env="conanrun")
