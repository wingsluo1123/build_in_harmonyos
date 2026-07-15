#!/usr/bin/env python3
"""Conan recipe for whois 5.6.6 — command-line WHOIS client.

whois is a client for the WHOIS protocol, used to query domain registration
information. It uses a simple Makefile build system.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WhoisConan(ConanFile):
    name = "whois"
    version = "5.6.6"
    description = "WHOIS client for querying domain registration information"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rfc1036/whois"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars
        compiler_executables = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        ar = compiler_executables.get("ar", "llvm-ar")
        ranlib = compiler_executables.get("ranlib", "llvm-ranlib")

        src = self.source_folder
        perl = os.environ.get("PERL", "perl")

        # Generate version.h from debian/changelog
        self.run(f"{perl} {src}/make_version_h.pl {src}/debian/changelog > {src}/version.h")

        # Build whois target only (mkpasswd fails on OHOS due to getpass)
        # R9: Always use -j1
        self.run(f"make -C {src} CC={cc} AR={ar} RANLIB={ranlib} whois -j1")

    def package(self):
        src = self.source_folder
        # Install the whois binary and man pages
        copy(self, "whois", src, os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", src, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.5", src, os.path.join(self.package_folder, "share", "man", "man5"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
