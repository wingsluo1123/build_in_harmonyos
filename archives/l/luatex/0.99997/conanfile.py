#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Luatex, luatex, 0.99997, LuaTeX 排版引擎，提供 lualatex 命令, GPL-2.0-or-later, https://github.com/TeX-Live/luatex
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LuatexConan(ConanFile):
    name = "luatex"
    version = "0.99997"
    description = "LuaTeX 排版引擎，提供 lualatex 命令"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/TeX-Live/luatex"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1.1")
        self.requires("fontconfig/2.16.0")
        self.requires("expat/2.8.2")
        self.requires("lua/5.2.4")
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["luatex"]
