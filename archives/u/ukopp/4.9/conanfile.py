#!/usr/bin/env python3
"""Conan recipe — ukopp 4.9 (plain Makefile, GTK3 backup application).

ukopp — disk-to-disk backup (Michael Cornelison, kornelix.com)：把挂载磁盘
或目录的文件复制到另一磁盘/目录（"备份盘"），支持全量/增量、校验
（mchecksum）、按天/周/月的版本保留（过期清理），GTK3 GUI 为主界面，
另有无 GUI 的命令行模式（`-nogui`，配合 `-job jobfile` / `-run jobfile`
可脚本化运行）。

License: GPL-3.0-or-later（doc/copyright；源文件头声明 version 3 or
later）。

适配要点：
- 上游为 2014 年裸 Makefile 工程（非 autotools）：默认目标编译
  ukopp-4.9.cc + zfuncs.cc（`pkg-config --cflags gtk+-3.0`）并链接
  `pkg-config --libs gtk+-3.0 -lpthread`；
- Makefile 未定义 CXX（make 缺省 g++）→ make 命令行传 CXX（R33：编译器
  从 tools.build:compiler_executables conf 获取，不用裸 ${CXX}）；
- PkgConfigDeps 生成 gtk+-3.0.pc / glib-2.0.pc 等（指向本机 conan 缓存
  绝对路径），显式把生成目录注入 PKG_CONFIG_PATH（bart-view 同款），
  Makefile 的 `pkg-config --cflags/--libs gtk+-3.0` 命中；
- 上游 `make install` 调用 xdg-desktop-menu（OHOS 无此工具）→ 不跑
  上游 install 目标，package() 手工布局产物（bin + share/ukopp/{data,
  icons} + share/doc + man1，与 Debian 包一致）；
- zfuncs.cc 以 `-D PREFIX -D DOCDIR` 编译期固化文档路径（缺省 /usr，与
  Debian 打包一致；仅影响 GUI 帮助文档定位，不影响 -nogui 命令行模式）；
- make -j1 SHELL=/bin/sh（R9/E074：HMDFS 不允许 jobserver FIFO）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class UkoppConan(ConanFile):
    name = "ukopp"
    version = "4.9"
    package_type = "application"
    description = ("ukopp - disk-to-disk backup: full and incremental "
                   "copies with verification and version retention "
                   "(GTK3 GUI + command line mode)")
    license = "GPL-3.0-or-later"
    homepage = "https://kornelix.com/ukopp"
    url = "https://kornelix.com/ukopp"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/**"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must accept Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported")

    def requirements(self):
        # zfuncs.h 直接 #include <gtk/gtk.h>，ukopp-4.9.cc/zfuncs.cc 全量
        # 使用 GTK3 C API（GUI + 命令行模式共用）→ transitive headers/libs
        #（mednaffe 同款）
        # glib 版本须与 gtk/3.24.43 的依赖闭包一致（gtk 固定 glib/2.84.0.1；
        # marco 同款搭配），否则图内版本冲突
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # gtk+-3.0.pc / glib-2.0.pc 等由 PkgConfigDeps 从依赖 cpp_info 生成
        # 到 generators 目录（本机 conan 缓存绝对路径）；显式注入
        # PKG_CONFIG_PATH（PkgConfigDeps 不自动设置该变量），供 Makefile 的
        # `pkg-config --cflags/--libs gtk+-3.0` 使用（bart-view 同款）。
        PkgConfigDeps(self).generate()
        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("conanbuild_pkgconfig")

    def _cxx(self):
        # R33: 编译器一律从 Conan conf 获取，不依赖 shell 环境变量
        cxxs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return cxxs.get("cpp") or "clang++"

    def build(self):
        # 补丁：ukopp-4.9.cc:1277 字符串字面量与 RSEP2 宏之间补空格
        #（C++11 -Wreserved-user-defined-literal，clang 15 硬错误；
        #  2014 年源码风格，gcc 老版本可编译）。marco 同款补丁机制。
        apply_conandata_patches(self)
        # 上游 Makefile in-source 编译（.o 与 ukopp 二进制生成在源码目录）；
        # 默认目标 = ukopp。CXX 命令行覆盖（Makefile 未定义 CXX），
        # CXXFLAGS/CFLAGS/LDFLAGS/PREFIX 走上游缺省（-O2 -Wall -ggdb、
        # -rdynamic -lpthread、/usr）。-j1 + SHELL=/bin/sh（R9/E074）。
        self.run("make -j1 SHELL=/bin/sh CXX=" + self._cxx(),
                 cwd=self.source_folder, env="conanbuild")
        if not os.path.isfile(os.path.join(self.source_folder, "ukopp")):
            raise ConanInvalidConfiguration("ukopp binary was not built")

    def package(self):
        # 上游 make install 依赖 xdg-desktop-menu（OHOS 无）→ 手工布局
        #（与 Debian 包一致）。data/（用户手册 + 图像）与 icons/ 供 GUI
        # 运行时读取（zdatadir/zicondir = $PREFIX/share/ukopp/{data,icons}）。
        copy(self, "ukopp", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "*", os.path.join(self.source_folder, "data"),
             os.path.join(self.package_folder, "share", "ukopp", "data"))
        copy(self, "*", os.path.join(self.source_folder, "icons"),
             os.path.join(self.package_folder, "share", "ukopp", "icons"))
        copy(self, "*", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "share", "doc", "ukopp"))
        # man page：上游 install 把 doc/ukopp.man 压缩为 man1/ukopp.1.gz；
        # 按仓库惯例平铺安装为 man1/ukopp.1
        copy(self, "ukopp.man", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "share", "man", "man1"))
        os.replace(os.path.join(self.package_folder, "share", "man", "man1", "ukopp.man"),
                   os.path.join(self.package_folder, "share", "man", "man1", "ukopp.1"))
        # desktop 入口（上游 install 为 share/applications/ukopp.desktop）
        copy(self, "desktop", self.source_folder,
             os.path.join(self.package_folder, "share", "applications"))
        os.replace(os.path.join(self.package_folder, "share", "applications", "desktop"),
                   os.path.join(self.package_folder, "share", "applications", "ukopp.desktop"))
        # 许可证（doc/copyright = GPL-3 声明与作者信息）
        copy(self, "copyright", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # ukopp 是单二进制应用：无公开头文件/导入库
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
