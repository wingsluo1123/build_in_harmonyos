#!/usr/bin/env python3
"""Conan recipe for htpdate 1.3.7 — HTTP Time Protocol synchronization tool.

htpdate synchronizes system time via HTTP headers from web servers.
Build system: raw Makefile (no configure).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HtpdateConan(ConanFile):
    name = "htpdate"
    version = "1.3.7"
    description = "HTTP Time Protocol synchronization tool"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/twekkel/htpdate"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf (dict-like), not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # R9: Use -j1
        # -D__OHOS__ enables adjtimex compatibility for OpenHarmony
        # -C to run make in the source directory (Makefile is there)
        self.run(
            f"make -C {self.source_folder} CC={cc} "
            f"CFLAGS=\"-Wall -std=c11 -pedantic -O2 -D__OHOS__\" -j1"
        )

    def package(self):
        copy(self, "htpdate", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "htpdate.8", self.source_folder, os.path.join(self.package_folder, "share/man/man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
