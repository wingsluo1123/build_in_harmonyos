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
        # CI 根因: apply_conandata_patches 找 source_folder/patches/ 但补丁在 export_sources_folder
        # Conan 2.x 消费者侧拉源码到 .conan2/p/.../s/，补丁需复制到 source_folder/patches/ 才找得到
        # 上轮 bug: src=recipe_folder/patches 在消费者侧不一定存在（补丁已 export 到 export_sources_folder）
        # 改从 export_sources_folder/patches 复制到 source_folder/patches（apply_conandata_patches 找的位置）
        patches_dst = os.path.join(self.source_folder, "patches")
        if not os.path.exists(os.path.join(patches_dst, "0001-atk-intl-wrapper.c.patch")):
            os.makedirs(patches_dst, exist_ok=True)
            # 优先从 export_sources_folder 找补丁（Conan 2.x 消费者侧补丁 export 位置）
            export_patches = os.path.join(self.export_sources_folder, "patches")
            recipe_patches = os.path.join(self.recipe_folder, "patches")
            src_patches = export_patches if os.path.exists(export_patches) else recipe_patches
            copy(self, "*.patch", src=src_patches, dst=patches_dst)
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
        # aireview P2: default_library 根据 shared 选项动态设（硬编码 static 致 shared=True 时产物仍 static 死选项）
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
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
        self.cpp_info.requires = ["glib::glib", "glib::gobject-2.0"]  # aireview High: 补 gobject-2.0 避消费者链接缺头/-lgobject-2.0
