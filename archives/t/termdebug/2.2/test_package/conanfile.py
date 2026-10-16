#!/usr/bin/env python3
"""Consumer test recipe for termdebug 2.2.

两段：
* 静态段（**任何环境都跑**）：包内容、5 个 argv[0] symlink、ELF 架构、
  man page / doc、以及"五个可选能力是否真的链进去了"的符号检查。
* 运行段（仅 can_run() 为真）：6 个 --help、5 个 -V、直接运行 termdebug 的
  分派拒绝消息。其中 tdreplay --help 里的 --visual-compare / --picture= /
  --picture-series= 是按 HAVE_CURSES+HAVE_UNISTRING / HAVE_CAIRO /
  HAVE_CAIRO+HAVE_PTHREAD 条件编译的，因此 --help 本身就是能力探针。

为什么用 can_run() 而不是"试一下能不能跑"：本机 WSL 注册了
binfmt_misc+qemu-aarch64，qemu 能把 aarch64 ELF 拉起来，于是 can_run 的
探测可能"成功"，但真正的加载器是 /lib/ld-musl-aarch64.so.1（一份旧的
musl），它没有 __vsnprintf_chk / __memcpy_chk / __strlen_chk 这些
_FORTIFY 符号 —— 制品仓的 cairo/1.18.4.2 需要它们（DevEco SDK 的
libc.so 三个都有，真机 OHOS loader 也能给）。于是执行会以 exit 127 +
"Error relocating ... symbol not found" 失败，那是本地模拟环境的缺陷，
不是包缺陷。交给 can_run() 判定（profile 里显式设了
tools.build.cross_building:can_run=false），把运行段留给真机 CI。
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TermdebugTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package = self.dependencies["termdebug"].package_folder
        script = os.path.join(self.recipe_folder, "test_termdebug.py")
        runnable = can_run(self)
        command = f'"{sys.executable}" "{script}" "{package}"'
        if runnable:
            command += " --runtime"
        self.run(command, env="conanrun")
        if not runnable:
            self.output.info(
                "termdebug: runtime leg skipped (cross build, can_run=False). "
                "The static leg still ran and asserted the real package content, "
                "so this is not a vacuous pass.")
