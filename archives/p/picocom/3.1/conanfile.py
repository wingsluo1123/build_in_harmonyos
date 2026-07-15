#!/usr/bin/env python3
"""Conan recipe — picocom 3.1 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PicocomConan(ConanFile):
    name = "picocom"
    version = "3.1"
    description = "Minimal dumb-terminal emulation program for serial port communication"
    license = "GPL-2.0"
    homepage = "https://github.com/npat-efault/picocom"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"

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
        # R33: Get compiler from Conan profile conf (dict), not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", {}) or {}
        cc = compilers.get("c", "clang") if isinstance(compilers, dict) else "clang"
        # R9: Use -j1, run in source folder where Makefile is
        self.run(f'cd {self.source_folder} && make CC={cc} CFLAGS="-Wall -g -fPIC -O2" LDFLAGS="-g" -j1')

    def package(self):
        # picocom has no install target; manually copy the binary from source
        copy(self, "picocom", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
