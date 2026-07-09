#!/usr/bin/env python3
"""Conan recipe — yadifa 3.0.5 (Autotools).

Lightweight authoritative Name Server with DNSSEC capabilities.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YadifaConan(ConanFile):
    name = "yadifa"
    version = "3.0.5"
    description = "Lightweight authoritative Name Server with DNSSEC capabilities"
    license = "BSD-3-Clause"
    homepage = "https://www.yadifa.eu"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6@ohpcd/stable")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Point to openssl from Conan dependency
        openssl_prefix = self.dependencies["openssl"].package_folder
        tc.configure_args.append(f"--with-openssl={openssl_prefix}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Run autoreconf in source folder to generate configure script
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["dnscore", "dnsdb", "dnslg"]
