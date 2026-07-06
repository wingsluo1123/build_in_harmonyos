#!/usr/bin/env python3
"""Conan recipe — bzip2 1.0.8 (Makefile build).

bzip2 is a system same-name library (libbz2), so it must be built
static-only (R26) to avoid polluting system library paths.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Bzip2Conan(ConanFile):
    name = "bzip2"
    version = "1.0.8"
    description = "High-quality data compressor - library and tools"
    license = "BSD-4-Clause"
    homepage = "https://sourceware.org/bzip2/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

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
        # R26: bzip2 is system same-name lib, build static only
        # R9: Always use -j1
        self.run("make CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1", cwd=self.source_folder)

    def package(self):
        # Copy headers
        copy(self, "bzlib.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Copy static library
        copy(self, "libbz2.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Copy executables
        for exe in ["bzip2", "bzip2recover", "bunzip2", "bzcat", "bzgrep", "bzmore", "bzless", "bzdiff"]:
            copy(self, exe, self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Library name is bz2 (libbz2.a)
        self.cpp_info.libs = ["bz2"]
        self.cpp_info.bindirs = ["bin"]
