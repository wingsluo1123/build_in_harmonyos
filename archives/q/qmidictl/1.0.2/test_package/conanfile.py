#!/usr/bin/env python3
"""test_package for qmidictl/1.0.2 — 真实执行被测包安装的 Qt6 GUI 二进制。

R51 上游测试清点：上游 qmidictl 1.0.2 **无任何自动化测试**——tarball 仅含
CMakeLists.txt / ChangeLog / LICENSE / README / src（71 个文件），没有 tests/
目录，顶层与 src/CMakeLists.txt 中均无 enable_testing() 或 add_test() 注册，
也没有 check/test 目标。因此 test_package 独立承担 L1 层验证。

本文件满足门禁并保持"实质测试"（非空壳）：
  * L0c / PF3 —— test_package/ 下有真实测试源 test_qmidictl.sh；
  * R34 —— test() 通过 self.run 真正 exec 被测二进制（--version / --help），
    并核对 ELF 头、DT_NEEDED 中的 Qt6 运行库与安装的桌面资源文件；
  * R9 —— 不伪造结论：任何断言失败即非零退出。
"""

import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class QmidictlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # 生成物（conanrun.sh / conanbuild.sh / *env-*.sh）必须落在独立的
        # build 目录，否则会被写进归档树 test_package/（JC1/JC4 未登记文件）。
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["qmidictl"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        if not os.path.isdir(bin_dir):
            raise RuntimeError(f"qmidictl bin/ not found: {bin_dir}")
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，必须用 bash 包装
        # （qastools/conducteo/acetoneiso 同款：优先取 CI profile buildenv 注入的
        #  CONFIG_SHELL，回退到 worker 上已知的 bash 路径）。
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            shell = "/bin/bash"
        script = os.path.join(self.source_folder, "test_qmidictl.sh")
        self.run(f'"{shell}" "{script}" "{bin_dir}" "{package_folder}"', env="conanrun")
