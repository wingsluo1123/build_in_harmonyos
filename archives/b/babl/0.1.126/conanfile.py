#!/usr/bin/env python3
"""Conan recipe template — Meson projects.

Usage: Replace Babl, babl, 0.1.126, \u50CF\u7D20\u683C\u5F0F\u8F6C\u6362\u5E93\uFF0C\u7528\u4E8EGEGL\u548C\, LGPL-3.0, https://gegl.org/babl/
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: default_library=static for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, load, save, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class BablConan(ConanFile):
    name = "babl"
    version = "0.1.126"
    description = "Babl - pixel format conversion library, used by GEGL"
    license = "LGPL-3.0"
    homepage = "https://gegl.org/babl/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.project_options["default_library"] = "static"
        tc.project_options["with-docs"] = "false"
        # Disable check-def-files target (fails on OHOS static builds)
        tc.project_options["enable-gir"] = "false"
        tc.generate()
        # Patch native file to add archiver (not auto-detected on OHOS)
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        content = load(self, native_file)
        content = content.replace(
            "cpp = '/data/service/hnp/bin/clang++'\n",
            "cpp = '/data/service/hnp/bin/clang++'\nar = '/data/service/hnp/bin/llvm-ar'\n"
        )
        save(self, native_file, content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["babl-0.1"]
