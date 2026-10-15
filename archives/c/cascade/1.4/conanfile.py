#!/usr/bin/env python3
"""Conan recipe for cascade 1.4 — RF cascade noise figure / gain / IIP3 analysis (sh + awk)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class CascadeConan(ConanFile):
    name = "cascade"
    version = "1.4"
    description = ("Noise figure, gain and third order intercept analysis of an RF "
                   "cascade, implemented as a POSIX sh + awk script")
    license = "BSD-4-Clause"
    homepage = "https://sourceforge.net/projects/rfcascade/"
    url = ""
    topics = ("rf", "noise-figure", "cli", "shell", "awk")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cascade targets POSIX systems only, got os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 无编译：configure 只探测 awk 与 install；`make cascade` 用 sed 把 @awk@/@version@
        # 写进 cascade.sh。
        # - 显式把 awk 解析名固定为 "awk"（configure 默认按 mawk/gawk/nawk/awk 顺序
        #   取构建机上先找到的名字，写进脚本后目标机不一定有同名命令）。
        # - 上游 configure 是 autoconf 2.13，不认 --host，故不使用 AutotoolsToolchain。
        # - 只构建 `cascade` 目标：默认 `all` 还会跑 `nroff -man` 预排版 cat1 手册页，
        #   而 nroff 不在 OHOS CI 工具链内（同类先例 wiggle/1.3、trurl/0.16.1）。
        self.run(f'AWK=awk ./configure --prefix="{self.package_folder}" '
                 f'--mandir="{self.package_folder}/share/man"',
                 cwd=self.source_folder)
        self.run("make cascade", cwd=self.source_folder)

    def package(self):
        # 等价于 `make install`，去掉依赖 nroff 的 install.man（cascade.1 源文件由下面 copy 安装）。
        self.run("make installdirs install.bin install.examples install.docs install.lisp",
                 cwd=self.source_folder)
        copy(self, "cascade.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        # installdirs 会建 man/cat1（预排版手册页目录），本包不生成 cat1，删除空目录。
        os.rmdir(os.path.join(self.package_folder, "share", "man", "cat1"))
        # 上游 README 引用的 COPYING 未随发布包分发，许可证声明在源文件头部。
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 产物只有解释型脚本与文档，与编译器/架构无关。
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
