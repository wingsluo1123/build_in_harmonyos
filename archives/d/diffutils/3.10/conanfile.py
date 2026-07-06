#!/usr/bin/env python3
"""Conan recipe — diffutils 3.10 (autotools).

diffutils provides diff, cmp, diff3, sdiff. Binary-only package.
gnulib is embedded in the source tree, not a separate dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DiffutilsConan(ConanFile):
    name = "diffutils"
    version = "3.10"
    description = "GNU diffutils - diff, cmp, diff3, sdiff"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/diffutils/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # gnulib is embedded in source, not a separate dependency

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        # diffutils is a set of binary tools, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
