#!/usr/bin/env python3
"""Conan recipe — gnupg 2.5.20 (Autotools, terminal application).

GnuPG is a complete implementation of the OpenPGP standard.
Produces multiple binaries: gpg, gpgv, gpgsm, gpg-agent, scdaemon, etc.

R26: Terminal tools must be statically linked.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnupgConan(ConanFile):
    name = "gnupg"
    version = "2.5.20"
    description = "GnuPG — GNU Privacy Guard, a complete OpenPGP implementation"
    license = "GPL-3.0-or-later"
    homepage = "https://gnupg.org/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libgpg-error/1.61")
        self.requires("libgcrypt/1.11.0")
        self.requires("libassuan/3.0.2")
        self.requires("libksba/1.6.7")
        self.requires("npth/1.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # HarmonyOS HMDFS: ./configure may fail with "Permission denied",
        # use sh ./configure to bypass execute-permission issues
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
