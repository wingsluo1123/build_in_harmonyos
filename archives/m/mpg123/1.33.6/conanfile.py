#!/usr/bin/env python3
"""Conan recipe — mpg123 1.33.6 (autotools).

mpg123 is a fast MPEG 1.0/2.0/2.5 audio player and decoder library.
Builds libmpg123 (static) and command-line tools (mpg123, out123, etc.).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Mpg123Conan(ConanFile):
    name = "mpg123"
    version = "1.33.6"
    description = "Fast MPEG 1.0/2.0/2.5 audio player and decoder library"
    license = "LGPL-2.1"
    homepage = "https://www.mpg123.org"
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
        tc = AutotoolsToolchain(self)
        # Build static library only (R26: system library static link)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
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
        self.cpp_info.libs = ["mpg123"]
