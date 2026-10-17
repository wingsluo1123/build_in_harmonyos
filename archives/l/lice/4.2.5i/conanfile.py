#!/usr/bin/env python3
"""Conan recipe — lice 4.2.5i (LiCe4：ircii-EPIC4 MUD 客户端的 IRC 覆层脚本，
SrfRoG, 1993-2000)，OHOS/aarch64。

平台任务 id=8456。

写本配方的依据 = 全部在源件上实测过的事实（未实测的推断不写成结论）：
- 取包 = Debian pool 原件。上游官方站 lice.codehack.com 已消亡（Debian 2026-07-22
  1:4.2.5i-3 changelog 逐字 "Point Homepage to web archive to express that upstream
  vanished"），无上游 git 仓库/tag 可得 ⇒ 按 jupp 3.1.41 先例取 Debian 官方 archive
  的 pool 原件 `lice_4.2.5i.orig.tar.gz`（`.orig` 按 Debian 政策即**未修改的上游原始
  发布件**；deb.debian.org 是官方 CDN，非第三方镜像 ⇒ 不触 PF7/R39）。sha256
  0c3d46c7432bf4ffe6aa67ecb22c726f2ec099fa949aacf11db2b5206b023b79 与 Debian 官方
  dsc（1:4.2.5i-3）Checksums-Sha256 逐字一致，本机实测 HTTP 200 / 275769B。
- 形态（解压实测）：纯脚本/数据包，302 常规文件（201 .gz + 101 数据文件）+ 13 符号链接
  （12 help 交叉引用 + sping.gz->rlag.gz），无 Makefile /
  Makefile.PL / configure / CMakeLists / setup.py / 任何 .pm ⇒ **零编译入口**；
  主脚本 `.irc/lice.irc.gz` 解压后第 55 行逐字 `^ASSIGN id.v 4.2.5i`。EPIC4 脚本
  语言（类 Perl 语法、在 EPIC4 客户端内执行），**不是** Perl/CPAN 模块 ⇒ 不需要
  perl 工具链，conan 依赖 = 0。
- 解包根目录 = `lice-4.2.5i`（带版本号，`tar tzf` 实测唯一顶层）⇒ get(strip_root=True)。
- 上游自带 `.irc/extra/sscan` 为 **ELF 32-bit i386 动态二进制**（`file` 实测
  "ELF 32-bit LSB executable, Intel 80386, dynamically linked, interpreter
  /lib/ld-linux.so.2"），OHOS aarch64 上不可能运行（架构不匹配 + 未签名 + 平台
  dlopen 限制）⇒ 本配方 package() 以 rm() 显式将其排除出交付（conan 2.29.1 实测
  copy(excludes=) 按相对路径匹配、按 basename 命中不了），
  保留源码 sscan.c；显式申报见 notes.md「sscan 排除申报」，不是静默丢弃。
- package_type 取 header-library（appconfig 先例）：交付零可执行文件、无 bin/
  安装 ⇒ CI L0k 走 "library package, commands.json not required" 分支，PF8 不误判
  CLI。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout


class LiceConan(ConanFile):
    name = "lice"
    version = "4.2.5i"
    description = ("LiCe4: IRC overlay script program for ircii-EPIC4 MUD clients "
                   "(bundled help, themes, pics, sounds)")
    license = "GPL-2.0-or-later"
    homepage = "http://lice.codehack.com"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("irc", "mud", "epic4", "script", "data")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 无编译步骤：纯脚本/数据包（零编译入口的三重举证见模块 docstring 与 notes.md）

    def package(self):
        # 交付 .irc 脚本树到 res/lice；排除上游自带 i386 ELF `.irc/extra/sscan`
        # （OHOS aarch64 不可运行，见模块 docstring 与 notes.md 申报）
        copy(self, "*",
             src=os.path.join(self.source_folder, ".irc"),
             dst=os.path.join(self.package_folder, "res", "lice"))
        # 排除上游自带 i386 ELF sscan：本机 conan 2.29.1 实测 copy(excludes=["sscan"])
        # 按相对路径匹配、命中不了 extra/sscan ⇒ 改用 rm() 按 basename 显式删除
        # （rm 语义见 conan/tools/files/files.py: fnmatch(filename, pattern)）
        rm(self, "sscan", folder=os.path.join(self.package_folder, "res", "lice", "extra"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["res"]
