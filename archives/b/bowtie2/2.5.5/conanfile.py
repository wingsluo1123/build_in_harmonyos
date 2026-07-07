#!/usr/bin/env python3
"""Conan recipe template — Makefile projects (SCAFFOLD, AI must adjust).

⚠️  This is a SCAFFOLD only. Makefile projects vary widely — each has different
    configure scripts, build targets, output names, and install rules.
    AI MUST review and adjust every method below before use.

Typical Makefile project types:
  1. Raw make (no configure, e.g. bzip2) — build() runs make directly
  2. Makefile + configure (e.g. zlib) — build() runs ./configure first, then make

Key rules:
  - R9:  Use make -j1 (not -j$(nproc))
  - R26: System-name libs (zlib, ncurses, etc.) must be static-only
  - R5:  Use CONFIG_SHELL for configure scripts (OHOS has no /bin/sh)
  -      Set env: os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

Usage: Replace Bowtie2, bowtie2, 2.5.5, 快速灵敏的带间隔读段比对工具，用于测序数据比对, GPL-3.0-or-later, https://bowtie2.sourceforge.net/
       Fill in requires(), build commands, and cpp_info.libs as needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Bowtie2Conan(ConanFile):
    name = "bowtie2"
    version = "2.5.5"
    description = "快速灵敏的带间隔读段比对工具，用于测序数据比对"
    license = "GPL-3.0-or-later"
    homepage = "https://bowtie2.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("simde/0.8.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R9: Always use -j1, never -j$(nproc)
        # SIMDE provides SSE2 emulation for aarch64
        simde_pkg = self.dependencies["simde"].package_folder
        simde_inc = os.path.join(simde_pkg, "include")
        cxxflags = f"-std=c++11 -I{simde_inc}"
        self.run(f"make -j1 CPP=clang++ CXX=clang++ CC=clang CXXFLAGS=\"{cxxflags}\"", cwd=self.source_folder)

    def package(self):
        # Bowtie2 builds executables
        copy(self, "bowtie2*", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.py", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.sh", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
