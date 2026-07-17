#!/usr/bin/env python3
"""Conan recipe for bzip2 1.0.8 — Makefile project.

bzip2 is a block-sorting file compressor and library.
Build system: raw Makefile (no configure script).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Bzip2Conan(ConanFile):
    name = "bzip2"
    version = "1.0.8"
    description = "高压缩比数据压缩工具和库，广泛用于 Linux 生态"
    license = "BSD-4-Clause"
    homepage = "https://sourceware.org/bzip2/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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

        # R33: Compiler is clang on OHOS, explicit in command not from env
        cc = "clang"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"

        # R9: Always use -j1
        if self.options.shared:
            # Build shared library via Makefile-libbz2_so
            self.run(f"cd {self.source_folder} && make -f Makefile-libbz2_so CC={cc} -j1")
        else:
            # Build static library and tools
            self.run(f"cd {self.source_folder} && make CC={cc} AR={ar} RANLIB={ranlib} -j1")

    def package(self):
        # Copy headers
        copy(self, "bzlib.h", self.source_folder, os.path.join(self.package_folder, "include"))
        # Copy libraries
        if self.options.shared:
            copy(self, "libbz2.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libbz2.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Copy executables
        copy(self, "bzip2", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bzip2recover", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["bz2"]
        self.cpp_info.bindirs = ["bin"]
