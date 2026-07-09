#!/usr/bin/env python3
"""Conan recipe for gmp 6.3.0 — Autotools project.

GMP is a free library for arbitrary precision arithmetic.
"""

import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GmpConan(ConanFile):
    name = "gmp"
    version = "6.3.0"
    description = "GNU Multiple Precision Arithmetic Library"
    license = "LGPL-3.0-or-later"
    homepage = "https://gmplib.org/"
    url = "https://gmplib.org/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure(args=[
            "--disable-shared",
            "--enable-static",
            "ABI=64"
        ])
        bash_path = shutil.which("bash") or "/usr/bin/env bash"
        autotools.make(args=[f"SHELL={bash_path}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gmp"]
        self.cpp_info.includedirs = ["include"]