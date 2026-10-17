#!/usr/bin/env python3
"""Conan test_package — spectools 201601r1（application 型）.

被测包是命令行工具集（无库导出），测试分两部分：
  1. 通用消费者冒烟测试（run_spectools_test.sh）：真实执行安装产物
     （R34/PF3 口径）—— spectool_raw -h/-l、spectool_curses -h、
     spectool_net -h（参数解析 + 用法/设备枚举输出，全部离线，无需
     Wi-Spy USB 硬件）。
  2. 鸿蒙平台特有测试（harmonyos_specific_test.c）：编译期硬绑定
     OHOS/AArch64 工具链 + 运行时校验 spectool_raw/spectool_curses/
     spectool_net 三个安装产物的 ELF64/EM_AARCH64/PT_INTERP/
     .note.ohos.ident/NEEDED libc.so 等平台属性。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class SpectoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 聚合 [buildenv]/buildenv_info 到 conanbuild.sh，使 build() 的
        # env="conanbuild" 可用（CC 注入 + 平台工具 PATH）
        VirtualBuildEnv(self).generate()

    def build(self):
        # 鸿蒙特有测试：用 OHOS clang 编译（编译期 __OHOS__/__aarch64__
        # 硬绑定，非鸿蒙工具链直接 #error）
        src = os.path.join(self.source_folder, "harmonyos_specific_test.c")
        out = os.path.join(self.build_folder, "harmonyos_specific_test")
        cc = self._select_cc()
        self.run('%s "%s" -o "%s" $CFLAGS' % (cc, src, out),
                 env="conanbuild")

    def _select_cc(self):
        """与主配方同一口径选编译器：优先 conf
        tools.build:compiler_executables（OHOS 交叉编译器），回退 PATH。
        WSL 上 PATH 裸 clang 是 x86_64 宿主编译器（__OHOS__ 未定义 →
        本测试的编译期守卫直接 #error），因此 conf 在位时必须以 conf 为准。"""
        try:
            exe = self.conf.get("tools.build:compiler_executables",
                                check_type=dict, default={})
        except Exception:
            exe = {}
        cand = exe.get("c")
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        return os.environ.get("CC") or shutil.which("clang") or "clang"

    def test(self):
        if cross_building(self):
            return

        pkg = self.dependencies["spectools"]
        raw = os.path.join(pkg.package_folder, "bin", "spectool_raw")
        curses = os.path.join(pkg.package_folder, "bin", "spectool_curses")
        net = os.path.join(pkg.package_folder, "bin", "spectool_net")

        # 1. 鸿蒙平台特有测试（编译期已绑 OHOS/AArch64）
        test_bin = os.path.join(self.build_folder, "harmonyos_specific_test")
        self.run('"%s" "%s" "%s" "%s"' % (test_bin, raw, curses, net),
                 env="conanrun")

        # 2. 通用消费者冒烟测试：真实执行被测包二进制
        script = os.path.join(self.source_folder, "run_spectools_test.sh")
        # HMDFS 上 chmod +x 不生效（E011），经 sh 解释器调用，不依赖执行位
        self.run('sh "%s" "%s" "%s" "%s"' % (script, raw, curses, net),
                 env="conanrun")
