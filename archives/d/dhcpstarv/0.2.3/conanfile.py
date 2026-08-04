#!/usr/bin/env python3
"""Conan recipe for dhcpstarv 0.2.3 — DHCP starvation utility.

Build system: autotools (autoreconf + configure + make).
No third-party C library dependency: uses Linux raw PF_PACKET sockets directly.
Patches: 0001 configure HMDFS tmpdir (applied after autoreconf), 0002/0003 OHOS musl udphdr members.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, patch, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DhcpstarvConan(ConanFile):
    name = "dhcpstarv"
    version = "0.2.3"
    description = "DHCP starvation utility (RFC2131), raw PF_PACKET sockets"
    license = "GPL-3.0"
    homepage = "https://github.com/sgeto/dhcpstarv"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/d/dhcpstarv/0.2.3"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # 0001 补丁不进入 conandata patches 列表（需在 autoreconf 后应用），手动导出
        copy(self, "0001-configure-hmdfs-tmpdir.patch",
             src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_sources_folder, "patches"))

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
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf()
        # configure 由 autoreconf 生成后，再应用 HMDFS 临时目录修复
        patch(self, patch_file=os.path.join(self.source_folder, "patches", "0001-configure-hmdfs-tmpdir.patch"))
        # HMDFS 上 config.status 临时目录需落在源码内 .tmp 目录（先创建）
        self.run("mkdir -p .tmp")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
