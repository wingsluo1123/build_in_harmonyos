#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Ytnef, ytnef, 2.1.2, ytnef 2.1.2, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YtnefConan(ConanFile):
    name = "ytnef"
    version = "2.1.2"
    description = "ytnef 2.1.2"
    license = "MIT"
    homepage = ""
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

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # ytnef tarball has no configure script, need autoreconf
        from conan.tools.files import save, load
        import subprocess
        subprocess.run(["autoreconf", "-vfi"], cwd=self.source_folder, check=True)
        # E011: Fix umask 077 -> 022 for HMDFS UID mapping compatibility
        subprocess.run(["sed", "-i", "s/umask 077/umask 022/g", "configure"],
                       cwd=self.source_folder, check=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ytnef"]
