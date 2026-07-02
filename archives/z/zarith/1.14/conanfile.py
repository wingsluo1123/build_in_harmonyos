#!/usr/bin/env python3
"""Conan recipe for ZArith 1.14 — OCaml big integer arithmetic library.

ZArith uses a custom configure script (not standard autotools).
Build: ./configure -installdir <dir> && make -j1 && make install
Dependencies: OCaml (system-installed), GMP (system-installed)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class ZarithConan(ConanFile):
    name = "zarith"
    version = "1.14"
    description = "Arithmetic and rational arithmetic library for OCaml"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/ocaml/Zarith"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GMP is system-installed at /storage/Users/currentUser/usr/local
        # Not available as Conan package in ohpcd channel
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment(self)
        # GMP is pre-installed at system prefix
        env.define("CFLAGS", "-I/storage/Users/currentUser/usr/local/include")
        env.define("LDFLAGS", "-L/storage/Users/currentUser/usr/local/lib")
        env.define("CC", "clang")
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # ZArith uses a custom configure script (not standard autotools)
        # The configure script takes -installdir, not --prefix
        install_dir = os.path.join(self.package_folder, "lib", "ocaml")
        self.run(f"./configure -installdir {install_dir}")
        self.run("make -j1")

    def package(self):
        # make install uses INSTALLDIR from configure
        self.run("make install")

    def package_info(self):
        self.cpp_info.libs = ["zarith"]
        self.cpp_info.libdirs = ["lib/ocaml/zarith"]
        self.cpp_info.includedirs = ["lib/ocaml/zarith"]
