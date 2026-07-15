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
        self.requires("expat/2.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # OHOS not recognized by config.guess; bypass with explicit triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # Use bundled versions for dependencies not yet in the registry
        tc.configure_args.append("--without-system-lua")
        tc.configure_args.append("--without-system-gmp")
        tc.configure_args.append("--without-system-mpfr")
        tc.configure_args.append("--without-system-fontconfig")
        tc.generate()

    def build(self):
        os.umask(0o022)  # HMDFS: 077 prevents writing to 700 dirs
        apply_conandata_patches(self)
        # Fix umask 077 → 022 in all configure scripts (HMDFS workaround)
        # config.status inherits umask 077 from configure, causing Permission denied
        for dirpath, _, filenames in os.walk(self.source_folder):
            for f in filenames:
                if f == "configure":
                    filepath = os.path.join(dirpath, f)
                    content = open(filepath).read()
                    if "umask 077" in content:
                        open(filepath, "w").write(content.replace("umask 077", "umask 022"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["luatex"]
