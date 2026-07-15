#!/usr/bin/env python3
"""Conan recipe for massdns 1.1.0 — high-performance DNS stub resolver.

MassDNS is a simple high-performance DNS stub resolver targeting those who
seek to resolve a massive amount of domain names. It is a command-line tool
built with a plain Makefile (no configure script).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MassdnsConan(ConanFile):
    name = "massdns"
    version = "1.1.0"
    description = "High-performance DNS stub resolver for batch DNS resolution"
    license = "GPL-3.0"
    homepage = "https://github.com/blechschmidt/massdns"
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
        # The Makefile uses $(CC), $(CFLAGS) etc. from the environment.
        # Conan's profile sets these via generated env files (conanbuild.sh).
        # R9: Always use -j1
        self.run(f"make -C {self.source_folder} -j1")

    def package(self):
        # massdns produces a single binary in {source_folder}/bin/
        copy(self, "massdns", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Man page
        copy(self, "massdns.1", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Application — no libraries, just a binary in bin/
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
