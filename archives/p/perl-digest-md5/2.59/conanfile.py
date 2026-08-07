#!/usr/bin/env python3
"""Conan recipe — Digest::MD5 Perl XS module (Makefile.PL + make).

Build system: Perl ExtUtils::MakeMaker (Makefile.PL)
This is a Perl XS module with C extension code (MD5.xs → MD5.c → MD5.so).

Digest::MD5 provides a Perl interface to the RSA MD5 Message-Digest Algorithm
(RFC 1321). The XS implementation provides high-performance native MD5 hashing.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlDigestMd5Conan(ConanFile):
    name = "perl-digest-md5"
    version = "2.59"
    description = "Perl interface to the MD-5 algorithm (Digest::MD5 XS module)"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://metacpan.org/dist/Digest-MD5"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — Digest::base and XSLoader are Perl core modules
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Perl XS module build: Makefile.PL generates Makefile, then make compiles C/XS code
        # R1: 参数最少化 — no PREFIX needed, system Perl config has correct CC/LDFLAGS
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Copy built artifacts to package folder in standard layout
        # .so goes to lib/auto/Digest/MD5/ (Perl auto path)
        # .pm goes to lib/Digest/ (Perl module path)
        src = self.source_folder
        blib_arch = os.path.join(src, "blib", "arch")
        blib_lib = os.path.join(src, "blib", "lib")

        copy(self, "MD5.so",
             src=os.path.join(blib_arch, "auto", "Digest", "MD5"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Digest", "MD5"))
        copy(self, "*.bs",
             src=os.path.join(blib_arch, "auto", "Digest", "MD5"),
             dst=os.path.join(self.package_folder, "lib", "auto", "Digest", "MD5"))
        copy(self, "MD5.pm",
             src=os.path.join(blib_lib, "Digest"),
             dst=os.path.join(self.package_folder, "lib", "Digest"))

    def package_info(self):
        # The shared library is MD5.so (Perl XS extension)
        self.cpp_info.libs = ["MD5"]
        self.cpp_info.libdirs = ["lib/auto/Digest/MD5"]
        self.cpp_info.includedirs = []
