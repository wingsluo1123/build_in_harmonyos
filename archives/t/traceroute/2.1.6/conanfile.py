#!/usr/bin/env python3
"""Conan recipe — traceroute 2.1.6

Traceroute network diagnostic tool. Uses a custom Makefile-based build system.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TracerouteConan(ConanFile):
    name = "traceroute"
    version = "2.1.6"
    description = "Traceroute network diagnostic tool - tracks the path packets take to a destination"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/traceroute/"
    url = ""  # CI fills this

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
        # R33: Use explicit compiler, not shell env vars
        # R9: Always use -j1
        src = self.source_folder
        self.run(f"make -C {src} env=yes CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1")

    def package(self):
        src = self.source_folder
        # Copy the traceroute binary from traceroute/ subdir
        copy(self, "traceroute", os.path.join(src, "traceroute"),
             os.path.join(self.package_folder, "bin"))
        # Copy man page
        copy(self, "traceroute.8", os.path.join(src, "traceroute"),
             os.path.join(self.package_folder, "share", "man", "man8"))
        # Copy header from libsupp/
        copy(self, "clif.h", os.path.join(src, "libsupp"),
             os.path.join(self.package_folder, "include"))
        # Copy library from libsupp/
        copy(self, "libsupp.a", os.path.join(src, "libsupp"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["supp"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
