#!/usr/bin/env python3
"""Conan recipe for lzlib - LZMA compression library.

Lzlib uses a custom configure script (not standard autotools).
The configure script hardcodes CC=gcc and falls back to CC=cc,
so CC must be passed as a configure argument, not via environment.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LzlibConan(ConanFile):
    name = "lzlib"
    version = "1.15"
    description = "LZMA library providing in-memory LZMA compression/decompression functions"
    license = "GPL-2.0+"
    homepage = "https://www.nongnu.org/lzip/lzlib.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # lzlib's custom configure hardcodes CC=gcc; pass CC as configure arg
        compiler_execs = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_execs.get("c")
        if cc:
            tc.configure_args.append(f"CC={cc}")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
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
        self.cpp_info.libs = ["lz"]
