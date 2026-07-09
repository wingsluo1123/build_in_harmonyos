#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Yubicocclient, yubico-c-client, 2.15, yubico-c-client 2.15, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YubicocclientConan(ConanFile):
    name = "yubico-c-client"
    version = "2.15"
    description = "yubico-c-client 2.15"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libcurl is a system dependency (precompiled package installed to ~/usr/local)
        # Not a Conan package - found via PKG_CONFIG_PATH in build environment
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # yubico-c-client is a library, not a terminal tool - no -static (R26)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Source tarball from GitHub archive does not include configure script
        self.run("autoreconf --install -f", cwd=self.source_folder)
        # HMDFS fix: umask 077 + setgid prevents file creation in temp dirs
        self.run("sed -i 's/umask 077/umask 022/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ykclient"]
