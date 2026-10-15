#!/usr/bin/env python3
"""Conan test_package for lpr 2008.05.17.4 — HarmonyOS consumer test.

两段，与 archives/t/termdebug/2.2/test_package 同构：

* 静态段（**任何环境都跑**）：包内容（bin/ 4 个 + sbin/ 4 个程序）、每个 ELF 的
  ELF64/小端/EM_AARCH64 头、8 份 man page、/etc/printcap、licenses/copyright，
  以及**compat 符号的作用域**——引用 musl 缺失的 rresvport_af/innetgr 的那 6 个程序
  必须在 .symtab 里把两个符号**定义为本地函数**（st_shndx != SHN_UNDEF），而
  lpf/lptest 必须完全不认识这两个符号（证明编译期驱动的链接注入范围是对的）。
* 运行段（仅 can_run() 为真）：5 个客户端 + lpc 对非法旗标打印用法（证明动态链接、
  getopt、printcap 子系统真的跑起来了）。lpd 不跑 —— 它是常驻守护进程；lpf/lptest
  需要真实参数与后端设备。

为什么用 can_run() 而不是"试一下能不能跑"：本机 WSL 注册了 binfmt_misc +
qemu-aarch64，aarch64 ELF 会被拉起来，但真正加载它的 /lib/ld-musl-aarch64.so.1
是一份不带 OHOS 专有符号的老 musl（lpd 引用 `__fd_chk`，那是 OHOS SDK
sys/select.h 里 FD_SET 的越界检查钩子，见 sysroot 的 sys/select.h:33）。本地模拟
环境的这个缺陷不是包缺陷，所以运行段交给 can_run() 判定（profile 里显式设了
tools.build.cross_building:can_run=false），留给真机 CI。
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LprTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv 把包内 bin/ 与 sbin/ 注入 PATH。
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["lpr"]
        script = os.path.join(self.recipe_folder, "test_lpr.py")
        command = '"%s" "%s" "%s"' % (sys.executable, script, dep.package_folder)
        if can_run(self):
            command += " --runtime"
        self.run(command, env="conanrun")
        if not can_run(self):
            self.output.info(
                "lpr: runtime leg skipped (cross build, can_run=False). The "
                "static leg still ran and asserted the real package content "
                "including the compat symbol scope, so this is not a vacuous "
                "pass.")