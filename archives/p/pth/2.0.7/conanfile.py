#!/usr/bin/env python3
"""Conan recipe for GNU Pth (Portable Threads) 2.0.7.

GNU Pth is a non-preemptive thread scheduling library.
License: LGPL-2.1-or-later
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PthConan(ConanFile):
    name = "pth"
    version = "2.0.7"
    description = "GNU Pth - The GNU Portable Threads library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/pth/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # pth uses relative paths (./shtool) - must build in-source
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Static linking - build static library only
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS doesn't support mkfifo (jobserver), use -j1
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = ["pth"]
