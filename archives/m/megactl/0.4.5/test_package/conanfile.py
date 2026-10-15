#!/usr/bin/env python3
"""megactl 0.4.5 test_package —— 消费者视角验证交付的两个 CLI。

两类真测试，都不依赖 MegaRAID 硬件：
  ① test_megactl.py —— 真执行 bin/megactl 与 bin/megasasctl，逐项断言真实退出码
     与真实 stderr/stdout 文案（选项解析、usage、target specifier 解析、
     device open 失败、ioctl 失败分支）。
  ② test_layout.py  —— 纯 Python 解析交付 ELF 字节，断言 ELF64/AArch64/PIE、
     DT_NEEDED 只含 musl libc.so、.interp 是 OHOS hnp loader、无构建机 RPATH，
     以及 man/metainfo/licenses 交付完整、无构建产物残留。

L1e（R34）反证：本测试真读 bin/ 下交付物并在包缺失时硬失败 —— CI 把 bin/ 移走后
本测试必然失败，因此不可能是空壳。
"""
import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class MegactlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # 必须显式声明：否则 generators（VirtualRunEnv 的 conanrun.sh 等）
        # 会落在 source_folder == test_package/ 里，把**构建机绝对路径**
        # （worktree 路径 + 宿主 PATH）写进待提交的目录。basic_layout 把
        # generators_folder 指向 build_folder，source_folder 仍是本目录，
        # 两个测试脚本照常按 recipe_folder 定位。
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkgdir = dep.package_folder
        bindir = os.path.join(pkgdir, "bin")
        src = self.source_folder
        # 两个脚本都用 recipe 里已 export 的测试源文件（test_type=explicit 时
        # source_folder 即 test_package/）
        cli = os.path.join(src, "test_megactl.py")
        layout = os.path.join(src, "test_layout.py")
        self.run(f'"{sys.executable}" "{cli}" "{bindir}"', env="conanrun")
        self.run(f'"{sys.executable}" "{layout}" "{pkgdir}"', env="conanrun")
