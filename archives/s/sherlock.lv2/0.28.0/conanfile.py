#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SherlockLv2Conan(ConanFile):
    name = "sherlock.lv2"
    version = "0.28.0"
    description = "Investigative LV2 plugin bundle（Atom/MIDI/OSC Inspector 插件）"
    license = "Artistic-2.0"
    homepage = "https://www.ventosus.ch/sherlock.lv2/"
    url = "https://git.ventosus.ch/sherlock.lv2"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # 导出 patches/ 目录（apply_conandata_patches 需要；multitail 教训）
    exports_sources = "patches/*"

    def requirements(self):
        # sherlock.lv2 的 DSP 插件依赖 LV2（>=1.14.0）；sratom 用于事件处理
        # （Arch PKGBUILD makedepends 确认），serd/sord 由 sratom 传递
        self.requires("lv2/1.18.11-git")
        self.requires("sratom/0.6.22-git")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        # meson 安装到 lib/lv2/sherlock.lv2（插件 bundle 目录）
        tc.project_options["lv2libdir"] = "lib/lv2"
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 应用 conandata.yml 注册的补丁（0001-disable-ui：禁用 OpenGL GUI 模块，
        # OHOS 无 GL/X11——multitail 教训：必须显式调用才会应用）
        apply_conandata_patches(self)

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
