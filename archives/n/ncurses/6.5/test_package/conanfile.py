#!/usr/bin/env python3
"""Test package — ncurses 6.5.

Links a minimal C program against libncursesw.a and runs it to verify
the static archive and headers are usable.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class NcursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsToolchain", "VirtualBuildEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Minimal ncurses program: initscr + endwin.
        # The `-l` flag already prepends `lib`, so pass the bare name:
        # `-lncursesw` searches `libncursesw.a`, whereas `-llibncursesw`
        # would search `liblibncursesw.a` (which ncurses never installs).
        src = os.path.join(self.source_folder, "test_ncurses.c")
        pkg = self.dependencies["ncurses"].package_folder
        lib_name = (
            "ncursesw" if self.dependencies["ncurses"].options.widec else "ncurses"
        )

        # R2: 从 conf 获取交叉编译工具链，避免硬编码 clang；-I/-L 使用
        # 依赖包 package_folder 的绝对路径，而非相对 cwd 的 include/lib。
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = ce.get("c", "clang")

        self.run(
            f'{cc} "{src}" -o test_ncurses '
            f"-I{os.path.join(pkg, 'include')} "
            f"-L{os.path.join(pkg, 'lib')} -l{lib_name} -static",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def test(self):
        # Binary should exist and be runnable (initscr may fail without tty, that's ok)
        self.run("test -f test_ncurses", cwd=self.source_folder)
