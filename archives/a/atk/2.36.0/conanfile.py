#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for ATK — Accessibility Toolkit for GNOME.

HarmonyOS PC (aarch64) adaptation. Uses Meson build system.
"""

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
import os

class AtkConan(ConanFile):
    name = "atk"
    version = "2.36.0"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/ATK"
    url = "https://wiki.gnome.org/Projects/ATK"
    description = "ATK is a toolkit for developing accessibility support."
    topics = ("accessibility", "gnome")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        # 仓库已上架 glib/2.84.0（2.88.0 未上架），降版到 2.84.0 避免 Conan 解析失败
        self.requires("glib/2.84.0")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def export_sources(self):
        # Conan 2.x: 复制配方本地补丁文件到导出缓存，
        # dst 追加 patches/ 层级与 conandata.yml patch_file 路径一致
        # CI 根因: dst=export_sources_folder 致补丁在根非 patches/ 下，
        # apply_conandata_patches 找 patches/0001-... 找不到 → source/target does not exist
        copy(self, "patches/*.patch",
             dst=os.path.join(self.export_sources_folder, "patches"),
             src=self.recipe_folder)

    def generate(self):
        tc = MesonToolchain(self)
        # OHOS: disable introspection to avoid build failures
        tc.project_options["introspection"] = "disabled"
        # glib 2.84.0 已通过 Conan 可用，禁用 meson fallback 克隆行为
        tc.project_options["wrap_mode"] = "nofallback"
        # P3: 固定 default_library=static（shared=False 契约生效）
        tc.project_options["default_library"] = "static"
        tc.generate()
        # P2: PkgConfigDeps 让 atk configure 通过 pkg-config 找到 glib
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["atk-1.0"]
        self.cpp_info.includedirs = ["include/atk-1.0"]
        self.cpp_info.set_property("pkg_config_name", "atk")
        # P1: 传播 glib 依赖给消费者，否则编译/链接必然失败
        self.cpp_info.requires = ["glib::glib"]
