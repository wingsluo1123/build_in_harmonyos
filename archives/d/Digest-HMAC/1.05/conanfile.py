#!/usr/bin/env python3
"""Conan recipe for Digest-HMAC — pure Perl module (Makefile.PL).

Build system: perl Makefile.PL + make + make install
No compiled code — pure Perl, no XS, no C dependencies.
Digest::SHA and Digest::MD5 are built into Perl 5.42+, no external deps.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DigestHmacConan(ConanFile):
    name = "digest-hmac"
    version = "1.05"
    description = "Perl HMAC (Keyed-Hashing for Message Authentication) module"
    license = "Perl Artistic License"
    homepage = "https://metacpan.org/pod/Digest::HMAC"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure Perl module — settings present for profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        # INSTALL_BASE gives a clean path without Perl version number
        self.run("perl Makefile.PL INSTALL_BASE=/usr/local", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = self.package_folder
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers can find the Perl modules
        perl_lib = os.path.join(self.package_folder, "usr", "local", "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
