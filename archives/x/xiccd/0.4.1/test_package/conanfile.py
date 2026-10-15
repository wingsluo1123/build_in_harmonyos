#!/usr/bin/env python3
"""xiccd 0.4.1 L1 测试 — 真实执行打包产物 bin/xiccd（R34：实质调用被测包，非空壳）。

xiccd 是命令行守护进程（package_type=application），无可链接库，因此测试不编译
任何客户端程序，而是直接跑安装出来的二进制并断言退出口径与输出：
  - `xiccd -V`      → exit 0，输出 "xiccd - Version 0.4.1"（验证 0001 补丁固化版本生效）
  - `xiccd --help`  → exit 0，usage 摘要含 "X color management daemon"
  - `xiccd --bad`   → exit 1（GOptionContext 解析失败路径可捕获，非崩溃）

CI/W3 无 X display，`xiccd` 的守护逻辑（RandR 监听 + colord D-Bus 推送）无法在
测试通道内跑通，故只做到二进制实际调用级（同 xsel/1.2.1、xclip 等 X11 命令行工具）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class XiccdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # 不可运行平台（交叉编译目标）直接跳过
        if not can_run(self):
            return
        bash = "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = "bash"
        self.run(f'"{bash}" test_xiccd.sh', env="conanrun", cwd=self.source_folder)
