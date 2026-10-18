#!/usr/bin/env python3
"""Conan test_package for interception-dual-function 1.5.0.

交付物是单个命令行可执行文件（interception-tools 插件，走 stdin/stdout 的
input_event 二进制流）。消费者侧测试分两部分：

  1) test_dfk.sh  —— 走上游公开接口（`-c <cfg.yaml>` + stdin/stdout 事件流）
     的功能断言：tap/hold 合成、未映射键与 EV_REL 透传、`-v`/`-h`、缺配置
     退出码（覆盖上游全部对外行为面）。
  2) test_ohos.sh —— 鸿蒙特有测试：ELF64/AArch64 身份、musl 解释器身份、
     NEEDED 无 Linux-only 条目，以及上游 calloc(0) 缺陷在 OHOS musl 下的
     崩溃回归探针（该缺陷在 glibc 上被掩盖，只在 OHOS musl 暴露）。
"""
import os

from conan import ConanFile


class InterceptionDualFunctionKeysTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg, "bin")
        self.run(f'bash "{self.recipe_folder}/test_dfk.sh" "{bin_dir}"',
                 env="conanrun")
        self.run(f'bash "{self.recipe_folder}/test_ohos.sh" "{bin_dir}"',
                 env="conanrun")
