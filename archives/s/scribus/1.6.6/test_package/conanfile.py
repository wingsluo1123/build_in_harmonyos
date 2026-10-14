#!/usr/bin/env python3
"""test_package for scribus/1.6.6 — 真实执行被测包安装的 scribus GUI 可执行文件。

上游 scribus 1.6.6 的 CTest 注册入口（enable_testing()）在主 CMakeLists.txt 被
注释，单元测试目标（scribus/tests）不随默认构建注册到 ctest；本 test_package
独立承担 L1 层验证，真实 exec 被测二进制并断言其 --version 输出。

本文件满足：
  * L0c —— test_package/ 下有真实测试源 test_scribus.sh；
  * L0d / PF3 —— test() 通过 self.run 真正 exec 被测二进制，非空壳；
  * R34 —— 断言落在被测包产出的可执行文件上（--version 输出 + ELF 头）。

headless 策略（R7：安全弹窗先触发再测试）：scribus 在进入 Qt 事件循环之前处理
--version（scribusapp.cpp ARG_VERSION "--version"，版本打印后退出），故在
QT_QPA_PLATFORM=offscreen 下可安全断言。
"""

import os

from conan import ConanFile
from conan.errors import ConanException


class ScribusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["scribus"].package_folder, "bin"
        )
        if not os.path.isdir(bin_dir):
            raise ConanException("scribus bin/ not found: %s" % bin_dir)
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，必须用 bash 包装
        # （qastools 同款：优先取 CI profile buildenv 注入的 CONFIG_SHELL，
        # 回退到 worker 上已知的 bash 路径）。
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_scribus.sh")
        self.run(f'"{shell}" "{script}" "{bin_dir}"', env="conanrun")
