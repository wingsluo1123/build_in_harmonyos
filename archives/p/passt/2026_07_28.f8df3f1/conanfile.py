#!/usr/bin/env python3
"""Conan recipe for passt — user-mode networking for VMs and containers.

passt uses a plain Makefile (no configure/cmake/autotools).
Build: make CC=clang
Install: make install DESTDIR=... prefix=...
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class PasstConan(ConanFile):
    name = "passt"
    version = "2026_07_28.f8df3f1"
    description = "Plug A Simple Socket Transport — user-mode networking for VMs and containers"
    license = "GPL-2.0-or-later"
    homepage = "https://passt.top/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.package = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self.run("make -j1")

    def package(self):
        self.run(f"make install DESTDIR={self.package_folder} prefix=/usr/local")

    def package_info(self):
        self.cpp_info.bindirs = ["usr/local/bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["usr/local/share"]
