#!/usr/bin/env python3
"""Conan recipe for libkeccak 1.4.3 — Keccak/SHA-3/SHAKE/RawSHAKE hashing library.

Build system: plain Makefile (no configure script).
libkeccak is NOT a system same-name library, so default dynamic linking is used.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibkeccakConan(ConanFile):
    name = "libkeccak"
    version = "1.4.3"
    description = "A Keccak/SHA-3/SHAKE/RawSHAKE hashing library"
    license = "MIT"
    homepage = "https://github.com/maandree/libkeccak"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libkeccak uses a plain Makefile, no autotools configure step.
        # CC and flags are passed via make variables in build()/package().
        pass

    def build(self):
        apply_conandata_patches(self)
        # Use -C to run make in the source directory (where Makefile lives).
        # Conan's build folder may be a subdirectory (e.g. build-release/).
        self.run(
            f"make -j1 -C {self.source_folder}"
            " CC=clang"
            " CFLAGS='-fPIC -O2'"
            " CPPFLAGS='-D_DEFAULT_SOURCE -D_BSD_SOURCE -D_XOPEN_SOURCE=700'"
        )

    def package(self):
        # Install into Conan package folder via DESTDIR + empty PREFIX.
        self.run(
            f"make -C {self.source_folder} install"
            f" DESTDIR={self.package_folder}"
            f" PREFIX="
            f" CC=clang"
        )

    def package_info(self):
        self.cpp_info.libs = ["keccak"]
