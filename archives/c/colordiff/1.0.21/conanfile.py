#!/usr/bin/env python3
"""Conan recipe for colordiff — a Perl script that colorizes diff output.

colordiff is a pure Perl script with no compilation step.
The Makefile provides an 'install' target that copies scripts,
man pages, and config files to the specified directories.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ColordiffConan(ConanFile):
    name = "colordiff"
    version = "1.0.21"
    description = "A tool to colorize diff output"
    license = "GPL-3.0-or-later"
    homepage = "https://www.colordiff.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Install using the Makefile's install target.
        # colordiff is a Perl script — no compilation, just file installation.
        # Use make -C to run in the source directory (Makefile is there).
        # DESTDIR is absolute, INSTALL_DIR/MAN_DIR/ETC_DIR are relative so
        # ${DESTDIR}${INSTALL_DIR} = <package_folder>/bin (Makefile convention).
        self.run(
            f"make -C {self.source_folder} install "
            f"DESTDIR={self.package_folder} "
            f"INSTALL_DIR=/bin "
            f"MAN_DIR=/share/man/man1 "
            f"ETC_DIR=/etc"
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
