#!/usr/bin/env python3
"""Conan recipe — fairymax 5.0b

Fairy-Max is a compact chess variant engine using XBoard protocol.
Builds three executables: fairymax, shamax, maxqi.
Plain Makefile project, no configure script.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FairymaxConan(ConanFile):
    name = "fairymax"
    version = "5.0b"
    description = "AI engine for chess variants (chess, xiangqi, shatranj, makruk)"
    license = "LicenseRef-Homebrew-public-domain"
    homepage = "https://deb.debian.org/debian/pool/main/f/fairymax/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # FAIRYDIR is compiled into the binary — set prefix to package_folder
        # so the binary knows where to find its data files at runtime.
        prefix = self.package_folder
        cflags = "-fPIC -O2"

        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" prefix="{prefix}" '
            f'-j1 fairymax shamax maxqi fairymax.6.gz',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "fairymax", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "shamax", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "maxqi", self.source_folder, os.path.join(self.package_folder, "bin"))

        copy(self, "*.ini", os.path.join(self.source_folder, "data"),
             os.path.join(self.package_folder, "share/games/fairymax"))
        copy(self, "*.hash", os.path.join(self.source_folder, "data"),
             os.path.join(self.package_folder, "share/games/fairymax"))

        copy(self, "*.eng", os.path.join(self.source_folder, "data"),
             os.path.join(self.package_folder, "share/games/plugins/xboard"))
        copy(self, "logo.png", os.path.join(self.source_folder, "data"),
             os.path.join(self.package_folder, "share/games/plugins/logos"))

        copy(self, "fairymax.6.gz", self.source_folder,
             os.path.join(self.package_folder, "share/man/man6"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
