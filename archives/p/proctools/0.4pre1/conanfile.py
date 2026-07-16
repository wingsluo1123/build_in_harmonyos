#!/usr/bin/env python3
"""Conan recipe for a /proc-based OHOS port of proctools 0.4pre1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ProctoolsConan(ConanFile):
    name = "proctools"
    version = "0.4pre1"
    description = "Process lookup and signaling tools: pgrep, pkill and pfind"
    license = "BSD-3-Clause AND BSD-4-Clause-UC"
    homepage = "https://proctools.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "files"),
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        copy(
            self,
            "proctools_ohos.c",
            src=os.path.join(self.export_sources_folder, "files"),
            dst=self.source_folder,
        )

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "proctools_ohos.c")
        for program in ("pgrep", "pkill", "pfind"):
            output = os.path.join(self.build_folder, program)
            self.run(
                '"{}" -O2 -std=c11 -D_GNU_SOURCE -DPROCTOOLS_NAME=\\\"{}\\\" '
                '"{}" -o "{}"'.format(cc, program, source, output)
            )

    def package(self):
        for program in ("pgrep", "pkill", "pfind"):
            copy(
                self,
                program,
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )
            copy(
                self,
                "{}.1".format(program),
                src=os.path.join(self.source_folder, program),
                dst=os.path.join(self.package_folder, "share", "man", "man1"),
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
