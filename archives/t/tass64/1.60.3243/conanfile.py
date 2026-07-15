#!/usr/bin/env python3
"""Conan recipe — tass64 1.60.3243

64tass is a multi pass optimizing macro assembler for the 65xx series
of processors (6502, 65C02, 65R02, 65816, etc).

Build system: simple Makefile (no configure script).
License: GPL-2.0-or-later AND LGPL-2.0-or-later AND LGPL-2.1-only AND MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Tass64Conan(ConanFile):
    name = "tass64"
    version = "1.60.3243"
    description = "Multi pass optimizing macro assembler for the 65xx series of processors"
    license = "GPL-2.0-or-later AND LGPL-2.0-or-later AND LGPL-2.1-only AND MIT"
    homepage = "https://tass64.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

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
        from conan.tools.gnu import AutotoolsToolchain
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan-generated environment, not raw shell vars.
        cc = os.environ.get("CC", "clang")
        # R9: Always use -j1 (OHOS does not support make jobserver, E074)
        self.run(f'make CC="{cc}" CFLAGS="-fPIC -O2" -j1')

    def package(self):
        # Install binary and man page using make install
        self.run(f'make install DESTDIR="{self.package_folder}" prefix=')

    def package_info(self):
        # tass64 is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
