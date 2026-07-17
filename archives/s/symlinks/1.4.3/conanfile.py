#!/usr/bin/env python3
"""Conan recipe for symlinks 1.4.3 — symbolic link scan/repair tool.

A simple Makefile project that produces a single binary.
No external dependencies, pure C using musl libc.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SymlinksConan(ConanFile):
    name = "symlinks"
    version = "1.4.3"
    description = "Symbolic link scan and repair tool"
    license = "MIT"
    homepage = "https://github.com/brandt/symlinks"
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

        # R33: Get compiler from Conan conf dict, never from shell env vars
        cc_info = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_info.get("c", "clang") if cc_info else "clang"

        # Run the dummy configure script (created by patch)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            self.run(f"sh {configure_path} --prefix={self.package_folder}")

        # R9: Always use -j1
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Copy the binary to bin/
        copy(self, "symlinks", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy man page
        copy(self, "symlinks.8", self.source_folder, os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
