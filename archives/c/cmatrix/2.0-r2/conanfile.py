#!/usr/bin/env python3
"""Conan recipe for cmatrix 2.0-r2 — autotools build system.

cmatrix is a terminal screensaver that displays scrolling lines of text.
Build: autotools with patches for OHOS platform compatibility.
"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CmatrixConan(ConanFile):
    name = "cmatrix"
    version = "2.0-r2"
    description = "Terminal screensaver displaying scrolling lines of text."
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/abishekvashok/cmatrix"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        self.run(f"{config_shell} ./autogen.sh", run_environment=True)
        self.run(f"CONFIG_SHELL={config_shell} CC={cc} {config_shell} ./configure --prefix=/",
                 run_environment=True)
        self.run("make -j1")

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]