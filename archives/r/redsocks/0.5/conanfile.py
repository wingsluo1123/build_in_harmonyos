#!/usr/bin/env python3
"""Conan recipe for redsocks 0.5 — transparent TCP-to-proxy redirector.

Build system: plain Makefile (no configure script).
Product: executable binary `redsocks`.
Dependency: libevent (libevent_core).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RedsocksConan(ConanFile):
    name = "redsocks"
    version = "0.5"
    description = "Transparent TCP-to-proxy redirector (SOCKS4/SOCKS5/HTTP-connect)"
    license = "Apache-2.0"
    homepage = "https://github.com/darkk/redsocks"
    url = "https://github.com/darkk/redsocks"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.12")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # Build flags from libevent dependency
        libevent_info = self.dependencies["libevent"]
        libevent_inc = libevent_info.cpp_info.includedirs[0]
        libevent_lib = libevent_info.cpp_info.libdirs[0]

        cflags = (
            f"-g -O2 -std=c99 -D_XOPEN_SOURCE=600 -D_DEFAULT_SOURCE "
            f"-D_GNU_SOURCE -Wall -I{libevent_inc}"
        )
        ldflags = f"-L{libevent_lib} -Wl,-rpath,{libevent_lib}"
        libs = "-levent_core"

        # R9: Always use -j1
        self.run(f"make CC={cc} CFLAGS='{cflags}' LDFLAGS='{ldflags}' LIBS='{libs}' -j1",
                 cwd=self.source_folder)

    def package(self):
        # redsocks has no `make install`, copy manually
        copy(self, "redsocks", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "redsocks.conf.example", self.source_folder, os.path.join(self.package_folder, "etc"))
        copy(self, "redsocks.service", self.source_folder, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
