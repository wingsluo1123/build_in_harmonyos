#!/usr/bin/env python3
"""Conan recipe — bonnie++ 2.00a (Autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BonnieConan(ConanFile):
    name = "bonnie++"
    version = "2.00a"
    description = "Bonnie++ - hard drive and file system benchmark"
    license = "GPL-2.0"
    homepage = "https://www.coker.com.au/bonnie++/"
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
        pass

    def build(self):
        apply_conandata_patches(self)
        # Fix shebang in configure script
        self.run("sed -i '1s|#!/bin/sh|#!/system/bin/sh|' configure || true", cwd=self.source_folder)
        # Set CC/CXX in environment
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"
        # Run configure
        self.run("./configure --prefix=/", cwd=self.source_folder)
        # Create empty depends file (Makefile includes it)
        depends_path = os.path.join(self.source_folder, "depends")
        if not os.path.exists(depends_path):
            open(depends_path, "w").close()
        # Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy executables
        copy(self, "bonnie++", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bon_csv2txt", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "bon_csv2html", self.source_folder, os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.1", self.source_folder, os.path.join(self.package_folder, "share/man/man1"))

    def package_info(self):
        self.cpp_info.libs = []
