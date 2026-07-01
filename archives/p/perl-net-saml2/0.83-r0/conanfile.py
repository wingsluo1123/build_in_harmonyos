#!/usr/bin/env python3
"""Conan recipe for perl-net-saml2 0.83-r0 (Net::SAML2).

Pure Perl module — SAML bindings and protocol implementation.
Build system: perl Makefile.PL (ExtUtils::MakeMaker).

R26: No C compilation, static linking N/A for pure Perl modules.
R27: No Conan dependencies (Perl runtime deps managed by CPAN/PERL5LIB).
R32: settings.os supports both Linux and OHOS.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Perlnetsaml2Conan(ConanFile):
    name = "perl-net-saml2"
    version = "0.83-r0"
    description = "SAML bindings and protocol implementation (Net::SAML2)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-SAML2"
    url = ""  # CI fills this

    # R32: Support both Linux and OHOS platforms
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any (R6: patch pipeline)
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        # R26: No C compilation; static linking not applicable for pure Perl
        self.run("perl Makefile.PL")
        self.run("make")

    def package(self):
        # Copy .pm files from blib/lib to package lib/ (G4 compatible layout)
        copy(self, "*.pm", src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # Copy .pod files if any
        copy(self, "*.pod", src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module: expose lib path via PERL5LIB
        perl_lib = os.path.join(self.package_folder, "lib")
        # Use runenv_info (Conan 2.x compatible, replaces deprecated env_info)
        self.runenv_info.prepend_path("PERL5LIB", perl_lib)
