#!/usr/bin/env python3
"""Conan recipe — dash 0.5.12 (shell, autotools).

dash is a POSIX-compliant shell. This is a binary-only package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DashConan(ConanFile):
    name = "dash"
    version = "0.5.12"
    description = "POSIX-compliant shell (Debian Almquist Shell)"
    license = "MIT"
    homepage = "http://gondor.apana.org.au/~herbert/dash/"
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
        # E011: Fix umask 077 -> 022 for HMDFS compatibility
        replace_in_file(self, os.path.join(self.source_folder, "configure"), "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # dash is a standalone binary, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
