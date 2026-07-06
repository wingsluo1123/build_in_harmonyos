#!/usr/bin/env python3
"""Conan recipe — bwfmetaedit 26.01 (Autotools, subdirectory build).

bwfmetaedit uses autotools in Project/GNU/CLI/ subdirectory.
Build: autoreconf → configure → make
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, patch, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BwfmetaeditConan(ConanFile):
    name = "bwfmetaedit"
    version = "26.01"
    description = "WAV/BWF metadata editor for Broadcast WAVE Format files"
    license = "BSD-3-Clause"
    homepage = "https://mediaarea.net/BWFMetaEdit"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        # Apply patches from conandata.yml
        apply_conandata_patches(self)

        # Generate configure script using autoreconf
        cli_dir = os.path.join(self.source_folder, "Project", "GNU", "CLI")
        self.run("autoreconf -fi", cwd=cli_dir)
        # Fix HMDFS umask 077 permission issue (E011)
        self.run("sed -i 's/umask 077/umask 022/g' configure", cwd=cli_dir)

        # Run configure + make in the CLI subdirectory
        # Use --prefix=/ so DESTDIR=package_folder yields package_folder/bin/
        self.run("./configure --prefix=/", cwd=cli_dir)
        self.run("make -j1", cwd=cli_dir)

    def package(self):
        cli_dir = os.path.join(self.source_folder, "Project", "GNU", "CLI")
        # Install: DESTDIR + --prefix=/ → package_folder/bin/bwfmetaedit
        self.run(f"make install DESTDIR={self.package_folder}", cwd=cli_dir)

    def package_info(self):
        # bwfmetaedit is an executable tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
