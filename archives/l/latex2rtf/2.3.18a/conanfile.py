#!/usr/bin/env python3
"""Conan recipe — latex2rtf 2.3.18a

latex2rtf converts LaTeX documents to RTF format.
Build system: simple Makefile (no configure script).
License: GPL-2.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Latex2RtfConan(ConanFile):
    name = "latex2rtf"
    version = "2.3.18a"
    description = "Converts LaTeX documents to RTF format"
    license = "GPL-2.0-or-later"
    homepage = "https://latex2rtf.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS platform compatibility
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
        pass

    def build(self):
        apply_conandata_patches(self)
        # latex2rtf is a pure Makefile project; CC and PREFIX are make variables
        # Use package_folder as PREFIX so CFGDIR matches the installed cfg path
        prefix = self.package_folder
        self.run(f'make CC=clang PREFIX="{prefix}" -j1')

    def package(self):
        # Copy the binary
        copy(self, "latex2rtf", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy configuration files (47 .cfg files)
        copy(self, "*.cfg", src=os.path.join(self.build_folder, "cfg"),
             dst=os.path.join(self.package_folder, "share", "latex2rtf", "cfg"))
        # Copy latex2png script
        copy(self, "latex2png", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.1", src=os.path.join(self.build_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # latex2rtf is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
