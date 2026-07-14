#!/usr/bin/env python3
"""Conan recipe — aamath 0.3 (Makefile).

aamath renders mathematical expressions as ASCII art text.
Build system: plain Makefile (no configure script).
Prebuilt readline/ncurses from DEFAULT_PREFIX (system libs, not Conan deps).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AamathConan(ConanFile):
    name = "aamath"
    version = "0.3"
    description = "Render mathematical expressions as ASCII art text"
    license = "GPL-2.0-or-later"
    homepage = "https://cdn.netbsd.org/pub/pkgsrc/distfiles/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aamath supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cxx = comp.get("cpp", "clang++") if comp else "clang++"

        sysroot = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
        src = self.source_folder

        self.run(
            f"make -f Makefile.good -j1 "
            f"CXX='{cxx}' "
            f"LD='{cxx}' "
            f"CXXFLAGS='-Wall -O2 -fPIC -DUSE_READLINE -I{sysroot}/include' "
            f"LFLAGS='-L{sysroot}/lib' "
            f"LIBS='-lreadline -lncurses'",
            env="conanbuild",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        self.run(
            f"make -f Makefile.good install "
            f"PREFIX=/ DESTDIR={self.package_folder}",
            env="conanbuild",
            cwd=src,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["readline", "ncurses"]
