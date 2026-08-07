#!/usr/bin/env python3
"""Conan recipe — Perl module MIME::Base32.

Pure Perl module using Makefile.PL (ExtUtils::MakeMaker) build system.
No C compilation, no shared libraries, no static linking needed.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Perlmimebase32Conan(ConanFile):
    name = "perl-mime-base32"
    version = "1.303"
    description = "Base32 encoding/decoding Perl module (RFC 3548 compatible)"
    license = "perl_5"
    homepage = "https://metacpan.org/pod/MIME::Base32"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module build: Makefile.PL -> make
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy .pm files from blib/lib to package lib/ for Conan artifact discovery (G4)
        copy(self, "*.pm", os.path.join(self.source_folder, "blib", "lib"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C libraries to link
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        # Expose Perl lib path for consumers via environment
        perl_lib = os.path.join(self.package_folder, "lib")
        self.runenv_info.append("PERL5LIB", perl_lib)
        self.buildenv_info.append("PERL5LIB", perl_lib)
