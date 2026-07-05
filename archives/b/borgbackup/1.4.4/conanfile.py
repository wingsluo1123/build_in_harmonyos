#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Borgbackup, borgbackup, 1.4.4, Deduplicating backup program with compression and authenticated encryption, MIT, https://www.borgbackup.org/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BorgbackupConan(ConanFile):
    name = "borgbackup"
    version = "1.4.4"
    description = "Deduplicating backup program with compression and authenticated encryption"
    license = "MIT"
    homepage = "https://www.borgbackup.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python3/3.14.5@ohpcd/stable")
        self.requires("openssl/3.6.2@ohpcd/stable")
        self.requires("liblz4/1.10.0@ohpcd/stable")
        self.requires("libzstd/1.5.6@ohpcd/stable")
        self.requires("libxxhash/0.8.2@ohpcd/stable")
        self.requires("msgpack/1.1.2@ohpcd/stable")
        self.requires("Cython/3.2.5@ohpcd/stable")
        self.requires("pkgconfig/1.6.0@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["borgbackup"]
