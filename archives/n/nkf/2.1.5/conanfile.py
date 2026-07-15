#!/usr/bin/env python3
"""Conan recipe — nkf 2.1.5

nkf (Network Kanji Filter) is a Japanese text encoding conversion tool.
It converts between various Japanese encodings (Shift_JIS, EUC-JP,
ISO-2022-JP, UTF-8, UTF-16, UTF-32, etc.).

Build system: simple Makefile (no configure script).
License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class NkfConan(ConanFile):
    name = "nkf"
    version = "2.1.5"
    description = "Network Kanji Filter - Japanese text encoding conversion tool"
    license = "MIT"
    homepage = "https://gitlab.com/nkf-developers/nkf"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in source directory — nkf's Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Compiler is clang per ohos-aarch64 profile (settings.compiler=clang)
        self.run('make CC=clang CFLAGS="-fPIC -O2 -Wall"')

    def package(self):
        # nkf is a command-line tool — copy binary and man page
        copy(self, "nkf", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "nkf.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # nkf is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
