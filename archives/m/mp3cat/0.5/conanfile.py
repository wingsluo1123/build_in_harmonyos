#!/usr/bin/env python3
"""Conan recipe for mp3cat 0.5 — CLI tool, plain Makefile build.

mp3cat is a simple MP3 stream concatenation tool. It uses a hand-written
Makefile (no configure script). Patches add CC/CFLAGS/LDFLAGS variable
support, DESTDIR for staging install, and --version/--help flags.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Mp3catConan(ConanFile):
    name = "mp3cat"
    version = "0.5"
    description = "mp3cat — concat MP3 streams, split into directory-based chunks"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tomclegg/mp3cat"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        # Set environment variables for make via conf_info
        cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
        self.conf_info.define("CC", cc)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars
        cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)

        # mp3cat uses a plain Makefile (no configure script)
        # R26: static linking via LDFLAGS=-static
        # R9: use -j1
        self.run(f"make CC={cc} CFLAGS='-O2' LDFLAGS='-static' -j1")

    def package(self):
        # Install binaries to package
        copy(self, "mp3cat", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        for script in ["mp3log", "mp3log-conf", "mp3dirclean", "mp3http", "mp3stream-conf"]:
            copy(self, script, src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["mp3cat"]
