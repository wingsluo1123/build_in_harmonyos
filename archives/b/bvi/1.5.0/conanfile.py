#!/usr/bin/env python3
# bvi 1.5.0 — OHOS aarch64 build recipe
"""Conan recipe — bvi 1.5.0 (Binary Visual Editor).

A vi-like hex editor for editing binary files.
Produces executables: bvi, bmore, bview (symlink), bvedit (symlink).

Build system: autotools (configure + make)
License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BviConan(ConanFile):
    name = "bvi"
    version = "1.5.0"
    description = "Binary Visual Editor - vi-like hex editor for binary files"
    license = "GPL-3.0-or-later"
    homepage = "http://bvi.sourceforge.net/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Force build triplet for HarmonyOS platform detection
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        # E001: On OHOS, cc/c++ symlinks don't exist, only clang/clang++
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # Manual install: out-of-source build breaks make install's file paths
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share/man/man1")
        helpdir = os.path.join(self.package_folder, "share/bvi")
        for d in [bindir, mandir, helpdir]:
            os.makedirs(d, exist_ok=True)
        # Binaries from build dir
        copy(self, "bvi", self.build_folder, bindir)
        copy(self, "bmore", self.build_folder, bindir)
        # Symlinks bview -> bvi, bvedit -> bvi
        for name in ["bview", "bvedit"]:
            link = os.path.join(bindir, name)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink("bvi", link)
        # Man pages and help file from source dir
        copy(self, "bvi.1", self.source_folder, mandir)
        copy(self, "bmore.1", self.source_folder, mandir)
        copy(self, "bmore.help", self.source_folder, helpdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["ncurses", "tinfo"]
