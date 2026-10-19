#!/usr/bin/env python3
"""Conan test_package for pnc 0.9.5（消费者视角，只用安装后的产物）。

验证安装出来的 bin/pnc：help/valid/format/find/info/dialout 真跑，
断言与上游 tests.sh 对齐并补充退出码与离线地理编码。
"""
import os

from conan import ConanFile


class PncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _shell(self):
        for cand in (os.environ.get("CONFIG_SHELL"),
                     "/data/service/hnp/bin/bash", "/bin/sh"):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return "sh"

    def test(self):
        pnc_pkg = self.dependencies["pnc"].package_folder
        env = f'export PNC_BIN="{os.path.join(pnc_pkg, "bin", "pnc")}" && '
        # 1) 断言型消费者测试（12 项，与上游 tests.sh 对齐）
        self.run(f'{env}{self._shell()} test.sh', env="conanrun")
        # 2) 鸿蒙真机端到端消费用例（文件进 → 联系人表出，五步串联）
        self.run(f'{env}{self._shell()} consumer-e2e.sh', env="conanrun")
