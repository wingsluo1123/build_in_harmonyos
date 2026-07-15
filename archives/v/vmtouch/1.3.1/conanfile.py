#!/usr/bin/env python3
"""Conan recipe — vmtouch 1.3.1

vmtouch - the Virtual Memory Toucher
Portable file system cache diagnostics and control.
Homepage: https://hoytech.com/vmtouch/
License: BSD-2-Clause
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class VmtouchConan(ConanFile):
    name = "vmtouch"
    version = "1.3.1"
    description = "Portable file system cache diagnostics and control"
    license = "BSD-2-Clause"
    homepage = "https://hoytech.com/vmtouch/"
    url = ""  # CI fills this

    package_type = "application"

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
        # R33: Get compiler from Conan conf, NEVER from shell env vars
        # tools.build:compiler_executables is a dict {c, cpp}, not a sub-conf
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # Only build the vmtouch binary (not vmtouch.8 which requires pod2man)
        self.run(f"make vmtouch CC={cc} CFLAGS='-Wall -O2 -g -std=c99 -fPIC' -j1",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "vmtouch", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # vmtouch is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
