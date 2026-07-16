#!/usr/bin/env python3
"""Conan recipe for the Tree-sitter 0.25 C runtime on HarmonyOS."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TreeSitterConan(ConanFile):
    name = "tree-sitter"
    version = "0.25"
    description = "Incremental parsing library for programming tools"
    license = "MIT"
    homepage = "https://tree-sitter.github.io/tree-sitter"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar")
        if not ar:
            compiler_dir = os.path.dirname(cc) if os.path.sep in cc else ""
            candidate = os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
            ar = candidate if candidate and os.path.isfile(candidate) else "llvm-ar"

        source = os.path.join(self.source_folder, "src", "lib.c")
        obj = os.path.join(self.build_folder, "libtree-sitter.o")
        archive = os.path.join(self.build_folder, "libtree-sitter.a")
        include = os.path.join(self.source_folder, "include")
        internal = os.path.join(self.source_folder, "src")

        self.run(
            '"{}" -O2 -fPIC -std=c11 -I"{}" -I"{}" -c "{}" -o "{}"'.format(
                cc, include, internal, source, obj
            )
        )
        self.run('"{}" rcs "{}" "{}"'.format(ar, archive, obj))

    def package(self):
        copy(
            self,
            "api.h",
            src=os.path.join(self.source_folder, "include", "tree_sitter"),
            dst=os.path.join(self.package_folder, "include", "tree_sitter"),
        )
        copy(
            self,
            "libtree-sitter.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tree-sitter"]
        self.cpp_info.set_property("cmake_file_name", "tree-sitter")
        self.cpp_info.set_property("cmake_target_name", "tree-sitter::tree-sitter")
        self.cpp_info.set_property("pkg_config_name", "tree-sitter")
