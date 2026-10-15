#!/usr/bin/env python3
"""Conan recipe for rover 1.0 — terminal file browser（单文件 C + ncursesw）。

Build system: 上游 Makefile
    `$(CC) $(CFLAGS) -o rover rover.c $(LDFLAGS) $(LDLIBS)`，LDLIBS=-lncursesw
依赖: ncurses/6.5（OHOS 下静态链接，宽字符库 = ncursesw）
OHOS 适配: 上游 Makefile 既不使用 pkg-config 也不接受依赖注入，交叉编译时
    必须把 conan 依赖的头/库路径显式写进 CFLAGS/LDFLAGS 并在 make 命令行
    覆盖（命令行变量优先级高于 Makefile 内赋值），否则会落到构建机系统
    /usr/include/curses.h，产出错误架构或直接编译失败。
    另需 -DNCURSES_WIDECHAR：rover 是宽字符 curses 程序，OHOS 的
    ncurses 头文件只有打开该宏才暴露 wchar 相关声明。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class RoverConan(ConanFile):
    name = "rover"
    version = "1.0"
    description = "Rover is a file browser for the terminal (ncurses)."
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/lecram/rover"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # OHOS 上 ncurses 只提供静态库；rover 为宽字符 curses 程序，链接 ncursesw
        self.requires("ncurses/6.5", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        dep = self.dependencies["ncurses"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        cflags = " ".join(f"-I{inc}" for inc in dep.cpp_info.includedirs)
        cflags += " -DNCURSES_WIDECHAR -Wall -O2"
        # 库名由上游 Makefile 的 LDLIBS=-lncursesw 提供，这里只补依赖库搜索路径
        ldflags = " ".join(f"-L{lib}" for lib in dep.cpp_info.libdirs)
        self.run(
            f"make -j1 -C {self.source_folder} CC={cc} "
            f"CFLAGS='{cflags}' LDFLAGS='{ldflags}'"
        )

    def package(self):
        copy(
            self,
            "rover",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "rover.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        for license_file in ("COPYING", "LICENSE"):
            if os.path.isfile(os.path.join(self.source_folder, license_file)):
                copy(
                    self,
                    license_file,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
