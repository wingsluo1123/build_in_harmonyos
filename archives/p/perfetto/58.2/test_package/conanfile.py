#!/usr/bin/env python3
"""test_package for perfetto 58.2 — 消费者视角验证已安装的 perfetto 工具链。

三件事（对应 PR 统计表的三行新增用例，互不重复计入）：
1. 消费者测试：编译并链接 libperfetto 的最小 C++ 程序并运行（consumer.cc）；
2. 消费者用例：以真实用户方式调用已安装 CLI（test.sh）；
3. 鸿蒙特有测试：AArch64 ELF + `.codesign` 段 + 只读 `/tmp` 下的 TMPDIR 约定（test_ohos.sh）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class PerfettoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 1) 消费者程序：链接 libperfetto（消费者测试）
        self.run(f"{bash} -c './consumer'", env="conanrun")
        # 2) 消费者用例：以真实用户方式调用已安装 CLI
        self.run(f"{bash} test.sh", env="conanrun")
        # 3) 鸿蒙平台特有校验（与消费者用例分开计数）
        self.run(f"{bash} test_ohos.sh", env="conanrun")
