#!/usr/bin/env python3
"""test_package for btrfs-compsize 1.5 — 消费者视角。

调用已安装的 `compsize` 二进制，走两条与宿主无关的 CLI 路径：
`--help`（打印用法 + exit 0）与空目录扫描（打印 "No files." + exit 1）。
两条路径都不触碰 btrfs 文件系统、不需要 root，因此在 OHOS CI worker 上是
确定性 oracle。
"""
import os

from conan import ConanFile


class BtrfsCompsizeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) 无法 exec ELF，须用 bash 包裹二进制执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
