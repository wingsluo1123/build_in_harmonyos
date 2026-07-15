#!/usr/bin/env python3
"""Conan recipe for kona — K programming language interpreter."""
import json
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class KonaConan(ConanFile):
    name = "kona"
    version = "20211225"
    description = "K programming language interpreter (Arthur Whitney's array language)"
    license = "ISC"
    homepage = "https://github.com/kevinlawler/kona"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except Exception:
                compilers = {}
        cc = compilers.get("c", "clang") if isinstance(compilers, dict) else "clang"
        self.run(f'make CC="{cc}" -j1 k')

    def package(self):
        copy(self, "k", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
