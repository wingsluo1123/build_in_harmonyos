#!/usr/bin/env python3
"""Conan recipe — Makefile projects (blind from suckless.org).

blind is a collection of command line video manipulation utilities.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BlindConan(ConanFile):
    name = "blind"
    version = "1.1"
    description = "Collection of command line video manipulation utilities for Unix"
    license = "ISC"
    homepage = "https://tools.suckless.org/blind/"
    url = ""  # CI fills this

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
        # blind uses a simple Makefile, build with clang
        self.run(f'make -C "{self.source_folder}" CC=clang -j1', env="conanrun")

    def package(self):
        # blind installs to DESTDIR/PREFIX
        self.run(f'make -C "{self.source_folder}" install DESTDIR="{self.package_folder}" PREFIX=""', env="conanrun")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
