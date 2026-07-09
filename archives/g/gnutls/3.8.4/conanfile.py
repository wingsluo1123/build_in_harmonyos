#!/usr/bin/env python3
"""Conan recipe for gnutls 3.8.4 — Autotools project.

GnuTLS is a secure communications library implementing TLS, SSL and DTLS protocols.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnuTLSConan(ConanFile):
    name = "gnutls"
    version = "3.8.4"
    description = "GNU Transport Layer Security library for secure communications"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnutls.org"
    url = "https://github.com/gnutls/gnutls"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("nettle/3.10.2")
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure(args=[
            "--with-included-libtasn1",
            "--disable-gost"
        ])
        bash_path = shutil.which("bash") or "/usr/bin/env bash"
        autotools.make(args=[f"SHELL={bash_path}"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "gnutls-cli", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "bin"))
        copy(self, "gnutls-serv", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["gnutls", "gnutlsxx"]
        self.cpp_info.includedirs = ["include"]
        self.conf_info.define("user.gnutls:cli", os.path.join(self.package_folder, "bin", "gnutls-cli"))