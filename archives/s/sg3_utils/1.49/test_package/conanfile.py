#!/usr/bin/env python3
"""test_package — sg3_utils 1.49 消费者验证 + 鸿蒙专项验证。

test():
  1. 编译并运行两个 C 用例（公开 API 消费 + 鸿蒙 sense 解码）；
  2. 实测上游 CLI 工具可执行（RC=0 自检）；
  3. 关键回归点：sg_dd 属上游 SG3_UTILS_LINUX_ONLY，只在
     `if (SG_LIB_LINUX AND NOT PT_DUMMY)` 分支构建（同批共 13 个工具 + sg_scan）。
     若 CMake 平台判定补丁失效落入 PT_DUMMY，该二进制不存在 → 本测试失败。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_sg3_utils"), env="conanrun")
        self.run(os.path.join(bindir, "test_sg3_utils_ohos"), env="conanrun")

        # 上游 CLI 可执行性自检（RC=0）；各工具打印的是自身版本（如 sg_inq 2.65），
        # 与包版本 1.49 不同，刻意不断言 1.49。
        for tool in ("sg_inq", "sg_vpd", "sg_turs"):
            self.run(f"{tool} --version", env="conanrun")

        # 真实 PT（非 PT_DUMMY）证据：LINUX_ONLY 工具只在真实 PT 分支构建
        for tool in ("sg_dd", "sg_copy_results"):
            self.run(f"{tool} --version", env="conanrun")
