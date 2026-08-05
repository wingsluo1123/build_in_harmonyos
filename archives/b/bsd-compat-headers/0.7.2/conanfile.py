#!/usr/bin/env python3
"""Conan recipe for bsd-compat-headers 0.7.2 — BSD compatibility headers for OpenHarmony.

Provides sys/cdefs.h, sys/queue.h, and sys/tree.h from FreeBSD.
Header-only package — no compilation needed.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches


class BsdCompatHeadersConan(ConanFile):
    name = "bsd-compat-headers"
    version = "0.7.2"
    description = "OpenHarmony 系统缺失的 BSD 兼容头文件（sys/cdefs.h, sys/queue.h, sys/tree.h）"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/bsd-compat-headers"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "src/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        # Header-only package: source files come from exports_sources
        pass

    def build(self):
        # Header-only package: no compilation step
        apply_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "sys"),
             dst=os.path.join(self.package_folder, "include", "sys"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
