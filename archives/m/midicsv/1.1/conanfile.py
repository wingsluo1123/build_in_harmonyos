#!/usr/bin/env python3
"""Conan recipe for midicsv — MIDI to CSV converter (command-line tool).

midicsv converts MIDI files to human-readable CSV text, and csvmidi converts
CSV back to MIDI. Both are standalone executables with no external dependencies.

Homepage: https://www.fourmilab.ch/webtools/midicsv/
License: Public Domain
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MidicsvConan(ConanFile):
    name = "midicsv"
    version = "1.1"
    description = "Convert MIDI audio files to human-readable CSV format and back"
    license = "Public Domain"
    homepage = "https://www.fourmilab.ch/webtools/midicsv/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

        # midicsv is a simple Makefile project with no configure script.
        # The patched Makefile already sets CC=clang, INSTALL=install.
        # Use source_folder since basic_layout separates build and source dirs.
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        self.run(f'make -C "{self.source_folder}" -j1 TMPDIR="{tmpdir}"')

    def package(self):
        # Copy built executables and man pages from source folder
        copy(self, "midicsv", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "csvmidi", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.5", self.source_folder, os.path.join(self.package_folder, "share", "man", "man5"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
