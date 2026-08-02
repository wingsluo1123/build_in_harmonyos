#!/usr/bin/env python3
"""Conan recipe for asymptote 3.12 — Autotools build system (configure + make).

Asymptote is a powerful descriptive vector graphics language for technical
drawing, providing a natural coordinate-based framework. Labels and equations
are typeset by LaTeX, producing high-quality PostScript/PDF output.

Build: ./configure && make && make install
Product: `asy` executable (vector graphics compiler — no linkable library)
Build system: autotools (configure + make)
"""
from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class AsymptoteConan(ConanFile):
    name = "asymptote"
    version = "3.12"
    description = "A powerful descriptive vector graphics language for technical drawing"
    license = "LGPL-3.0-or-later"
    homepage = "https://asymptote.sourceforge.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        # asymptote 是可执行工具, OHOS 平台无需 shared 库选项
        if self.settings.os == "OHOS":
            self.options.rm_safe("shared")
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 平台需显式指定 build 类型, 避免 config.guess 识别失败
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # 关闭可选依赖, 减少鸿蒙平台缺失库的编译阻碍
        if self.settings.os == "OHOS":
            tc.configure_args.append("--disable-ffmpeg")
            tc.configure_args.append("--disable-gc")
            tc.configure_args.append("--disable-gsl")
            tc.configure_args.append("--disable-gl")
            tc.configure_args.append("--disable-vulkan")
            tc.configure_args.append("--disable-lsp")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # GNU make 4.4 defaults to a FIFO jobserver, which OHOS disallows.
        autotools.make(args=["--jobserver-style=pipe", "-j4"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # asymptote 是可执行文件, 非可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
# OHOS-CI-trigger: re-run build @ 2026-08-02 21:12 (no functional change)
