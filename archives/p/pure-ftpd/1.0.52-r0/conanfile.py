#!/usr/bin/env python3
"""Conan recipe for pure-ftpd — a free, secure, production-quality and standard-conformant FTP server.

Autotools-based build with TLS support via OpenSSL.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class PureFtpdConan(ConanFile):
    name = "pure-ftpd"
    version = "1.0.52-r0"
    description = "Free, secure, production-quality and standard-conformant FTP server"
    license = "BSD-2-Clause"
    homepage = "https://www.pureftpd.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("--with-everything")
        tc.configure_args.append("--with-tls")
        tc.configure_args.append("--with-altlog")
        tc.configure_args.append("--with-puredb")
        tc.configure_args.append("--with-extauth")
        tc.configure_args.append("--with-cookie")
        tc.configure_args.append("--with-throttling")
        tc.configure_args.append("--with-ratios")
        tc.configure_args.append("--with-quotas")
        tc.configure_args.append("--with-ftpwho")
        tc.configure_args.append("--with-uploadscript")
        tc.configure_args.append("--with-virtualhosts")
        tc.configure_args.append("--with-virtualchroot")
        tc.configure_args.append("--with-diraliases")
        tc.configure_args.append("--with-peruserlimits")
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()

        # Fix statvfs64 false positive: configure detects statvfs64() as
        # available but struct statvfs64 is only forward-declared on OHOS.
        # Undefine HAVE_STATVFS64 so the code falls back to struct statvfs.
        replace_in_file(self, "config.h",
                        "#define HAVE_STATVFS64",
                        "/* #undef HAVE_STATVFS64 */")

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
