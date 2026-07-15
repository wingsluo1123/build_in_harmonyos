#!/usr/bin/env python3
"""Conan recipe for minimap2 2.30 — a versatile pairwise aligner for genomic sequences.

minimap2 is a C library + CLI tool for nucleotide sequence alignment.
Build: make arm_neon=1 aarch64=1 (NEON via sse2neon on aarch64)
Products: minimap2 binary + libminimap2.a static library
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Minimap2Conan(ConanFile):
    name = "minimap2"
    version = "2.30"
    description = "A versatile pairwise aligner for genomic and spliced nucleotide sequences"
    license = "MIT"
    homepage = "https://github.com/lh3/minimap2"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = "llvm-ar"

        # minimap2 uses a plain Makefile (no configure script).
        # arm_neon=1 enables NEON SIMD via sse2neon header translation.
        # aarch64=1 selects aarch64-specific CFLAGS (-D_FILE_OFFSET_BITS=64 -fsigned-char).
        cflags = " ".join([
            "-O2",
            "-fPIC",
            "-Wall",
            "-Wc++-compat",
            "-D_FILE_OFFSET_BITS=64",
            "-fsigned-char",
        ])

        # R9: Use -j1 to avoid parallel build issues on OHOS
        self.run(
            f"make arm_neon=1 aarch64=1 "
            f"CC={cc} AR={ar} "
            f'CFLAGS="{cflags}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        # Install binary, library, headers, and man page
        copy(self, "minimap2", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "libminimap2.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "minimap2.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = ["minimap2"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.bindirs = ["bin"]
