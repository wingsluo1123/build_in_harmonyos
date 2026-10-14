#!/usr/bin/env python3
"""Conan recipe for Wumpus 1.12 (Makefile)."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class WumpusConan(ConanFile):
    name = "wumpus"
    version = "1.12"
    description = "Hunt the Wumpus and Superhack text games"
    license = "BSD-2-Clause"
    homepage = "https://www.catb.org/~esr/wumpus/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Preserve one executable through make expansion and both shells.
        cc_assignment = "CC=" + shlex.quote(cc).replace("$", "$$")
        self.run(
            f"make {shlex.quote(cc_assignment)} -j1", cwd=self.source_folder
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "wumpus", self.source_folder, bindir)
        copy(self, "superhack", self.source_folder, bindir)
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
