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
        ret = self.run(f"{cc} -I{inc} -L{lib} -o test_ncurses test.c -lncursesw", cwd=self.build_folder)
        if ret != 0:
            raise ConanException(f"compile test_ncurses failed with exit code {ret}")

    def test(self):
        if can_run(self):
            ret = self.run("./test_ncurses", env="conanrun")
            if ret != 0:
                raise ConanException(f"test_ncurses failed with exit code {ret}")
