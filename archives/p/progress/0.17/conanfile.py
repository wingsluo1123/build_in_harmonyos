#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class ProgressConan(ConanFile):
    name = "progress"
    version = "0.17"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 依赖：ncurses（progress 的 Makefile 用 pkg-config 检测 ncursesw——
    # registry 已合入 ncurses/6.5）
    requires = "ncurses/6.5"

    def layout(self):
        basic_layout(self)

    def generate(self):
        # progress 的 Makefile 用 pkg-config ncursesw 检测——PKG_CONFIG_PATH
        # 指向 ncurses 包 pkgconfig（alpine/fizmo 的 ncurses 处理先例）
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", os.path.join(
            self.dependencies["ncurses"].package_folder, "lib", "pkgconfig"))
        env.vars(self).save_script("conanbuild_pkgconfig")

    def build(self):
        # progress 无 configure（纯 Makefile 项目——notes.md 确认）；
        # CC=clang：Makefile 默认 CC=cc 但 OHOS 仅有 clang（multitail 先例）；
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
        self.run("make -j1 CC=clang", cwd=self.source_folder,
                 env="conanbuild")

    def package(self):
        # Makefile install 支持 DESTDIR+PREFIX（第 33 行 install 目标——
        # Installing program to $(DESTDIR)$(BINDIR)）
        self.run("make install DESTDIR={} PREFIX=/usr".format(
            os.path.join(self.package_folder)), cwd=self.source_folder,
            env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
