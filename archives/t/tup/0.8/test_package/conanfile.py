#!/usr/bin/env python3
"""test_package for tup 0.8 — 可执行包（CLI）的消费者验证。

tup 交付的是 CLI（bin/tup）+ 依赖注入库（bin/tup-ldpreload.so），不是库。
test() 通过 bash 执行 test.sh，test.sh 以真实用户视角调用 CLI 并断言可观测结果：

  1. `tup --version` 输出内置版本串（验证 TUP_LABEL 生效）
  2. `tup server` 报告 ldpreload（验证 HarmonyOS 平台分支生效）
  3. bin/tup-ldpreload.so 与 tup 同目录（depfile.c 的硬性要求）
  4. 端到端：一个用 touch 产出输出的规则能构建成功，且未变更时二次执行不重建
     （这一条正是本次适配修复的核心行为，见 patches/0002）

OHOS: /system/bin/sh (mksh) 不能可靠执行 ELF 二进制，统一用 bash 包一层。
"""
import os

from conan import ConanFile


class TupTestConan(ConanFile):
    """test_package for tup executable — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
