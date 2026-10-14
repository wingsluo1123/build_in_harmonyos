#!/usr/bin/env python3
"""Conan recipe for Modest 0.0.6 — pure C99 HTML renderer (GNU Make).

Build: make clone library && make install prefix=<pkg>.
Produces libmodest.so / libmodest_static.a plus headers (include API).
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ModestConan(ConanFile):
    name = "modest"
    version = "0.0.6"
    description = "Modest — fast HTML renderer library implemented as a pure C99 library with no outside dependencies"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lexborisov/Modest"
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

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # MODEST_CFLAGS is assembled inside the Makefile with `?=` + `+=`;
        # overriding it on the command line drops internal flags (-Isource etc.).
        # CFLAGS is not defined by the Makefile, so it is the safe injection
        # point for the clang-15 cast warning suppression (-Werror is internal).
        cflags = "-fPIC -O2 -Wno-void-pointer-to-enum-cast"

        # R9: always -j1
        self.run(f"make clone CC={cc} CFLAGS='{cflags}' -j1", cwd=self.source_folder)
        self.run(f"make library CC={cc} CFLAGS='{cflags}' -j1", cwd=self.source_folder)

    def package(self):
        # Makefile install writes to $(DESTDIR)$(prefix)/lib and /include
        self.run(f"make install prefix={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["modest"]
