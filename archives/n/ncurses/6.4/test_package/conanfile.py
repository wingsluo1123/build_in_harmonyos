#!/usr/bin/env python3
"""Conan test_package — ncurses 6.4 smoke test (link against libncursesw.a)."""
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class NcursesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "AutotoolsToolchain", "AutotoolsDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译 test.c 链接 libncursesw 验证静态库可用
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        inc = os.path.join(self.dependencies["ncurses"].package_folder, "include")
        lib = os.path.join(self.dependencies["ncurses"].package_folder, "lib")
        # aireview P3: self.run 自带非零退出码抛 ConanException，手动 ret=if raise 是死代码删
        self.run(f"{cc} -I{inc} -L{lib} -o test_ncurses {os.path.join(self.source_folder, 'test.c')} -lncursesw", cwd=self.build_folder)

    def test(self):
        if can_run(self):
            # P2: self.run 非零退出码先抛 ConanException，77-SKIP 分支不可达
            # 改 ignore_errors=True 使退出码返回给 if ret == 77 判断
            ret = self.run("./test_ncurses", env="conanrun", ignore_errors=True)
            if ret == 77:
                # SKIP 退出码：OHOS 无终端时 initscr 返回 NULL，测试跳过而非失败
                self.output.info("test_ncurses: SKIP (no terminal available)")
                return
            if ret != 0:
                # P3: ret==77 是上游约定的"特性不可用"退出码，其他非零是真实失败
                # 但 ret==77 分支已上面处理，这里 ret!=0 非 77 是真实失败 → 让 self.run 抛异常避死代码
                raise ConanException(f"test_ncurses failed with exit code {ret} (not 77, real failure)")
