#!/usr/bin/env python3
"""Conan recipe for dhcpstarv 0.2.2 — DHCP starvation utility.

Build system: autotools (configure + make，无需 autoreconf).
No third-party C library dependency: uses Linux raw PF_PACKET sockets directly.
Patches: 0000 预生成 autotools 文件（configure/aclocal.m4/Makefile.in/src/Makefile.in/config.h.in
        及顶层 aux 脚本），0001 configure HMDFS tmpdir，0002/0003 OHOS musl udphdr members。
"""
import os
import stat
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class DhcpstarvConan(ConanFile):
    name = "dhcpstarv"
    version = "0.2.2"
    description = "DHCP starvation utility (RFC2131), raw PF_PACKET sockets"
    license = "GPL-3.0"
    homepage = "https://github.com/sgeto/dhcpstarv"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/d/dhcpstarv/0.2.2"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # 上游 Makefile.am 使用 nostdinc，config.h 与源文件同目录查找；采用 in-source 构建
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-silent-rules")
        tc.generate()

    def build(self):
        # 按 conandata 顺序应用补丁：0000 预生成文件 → 0001 HMDFS → 0002/0003 udphdr
        apply_conandata_patches(self)
        # patch 应用后 configure 等脚本丢失可执行位，恢复（R19 产物由 CI 构建，此为非产物脚本权限修复）
        for fn in ("configure", "config.status", "config.sub", "config.guess",
                   "install-sh", "missing", "depcomp"):
            p = os.path.join(self.source_folder, fn)
            if os.path.exists(p):
                os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # HMDFS 上 config.status 临时目录需落在源码内 .tmp 目录（先创建）
        self.run("mkdir -p .tmp")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
