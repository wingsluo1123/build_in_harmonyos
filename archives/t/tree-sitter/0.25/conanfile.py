#!/usr/bin/env python3
"""Conan recipe for tree-sitter 0.25 — Makefile project.

tree-sitter is an incremental parsing system for programming tools.
It builds a C library (libtree-sitter.a / libtree-sitter.so) using a
plain Makefile (no configure step required).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TreesitterConan(ConanFile):
    name = "tree-sitter"
    version = "0.25"
    description = "An incremental parsing system for programming tools"
    license = "MIT"
    homepage = "https://tree-sitter.github.io/tree-sitter/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tree-sitter supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        # R9: Always use -j1
        # Use -C to point make at the source folder where the Makefile lives
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        # Copy header from lib/include/tree_sitter/api.h
        copy(self, "tree_sitter/api.h",
             os.path.join(self.source_folder, "lib", "include"),
             os.path.join(self.package_folder, "include"))
        # Copy static library
        copy(self, "libtree-sitter.a",
             self.source_folder,
             os.path.join(self.package_folder, "lib"))
        # Copy shared library and symlinks if shared option is set
        if self.options.shared:
            copy(self, "libtree-sitter.so*",
                 self.source_folder,
                 os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tree-sitter"]
