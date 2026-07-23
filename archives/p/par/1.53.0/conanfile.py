#!/usr/bin/env python3
"""Conan recipe for par 1.53.0 — Paragraph reflow for email.

par is a command-line tool that reformats paragraphs of text.
Build system: protoMakefile (custom Makefile, not autotools/cmake).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ParConan(ConanFile):
    name = "par"
    version = "1.53.0"
    description = "Paragraph reflow for email — intelligent paragraph reformatter"
    license = "MIT-like"
    homepage = "https://bitbucket.org/amc-nicemice/par"
    url = "https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/tree/main/archives/p/par/1.53.0"

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

        # R33: Get compiler from Conan conf, not shell env vars
        cc_conf = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = cc_conf.get("c", "clang")

        # par uses protoMakefile (custom Makefile, not autotools/cmake)
        # CC in protoMakefile includes compile flags per its design
        # R9: Always use -j1
        self.run(f'make -f protoMakefile CC="{cc} -fPIC -O2 -c" LINK1={cc} LINK2=-o -j1',
                 cwd=self.source_folder)

    def package(self):
        # par is a CLI tool — install binary and man page
        copy(self, "par", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "par.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
