#!/usr/bin/env python3
"""Conan recipe for perl-package-deprecationmanager 0.18-r1 (Package::DeprecationManager CPAN module).

This is a pure-Perl module built with ExtUtils::MakeMaker (Makefile.PL).
Build steps: perl Makefile.PL -> make -> make install

Dependencies: Package::Stash, Params::Util, Sub::Install, Sub::Util, List::Util, Carp
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlPackageDeprecationManagerConan(ConanFile):
    name = "perl-package-deprecationmanager"
    version = "0.18-r1"
    description = "Manage deprecation warnings for your distribution (Package::DeprecationManager CPAN module)"
    license = "artistic_2"
    homepage = "https://metacpan.org/dist/Package-DeprecationManager"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl-package-stash/0.40-r1")

    def layout(self):
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        # Set INSTALL_BASE at Makefile.PL time so install targets use it
        self.run("perl Makefile.PL INSTALL_BASE={}".format(self.package_folder))
        self.run("make")

    def package(self):
        # Install using the INSTALL_BASE set during Makefile.PL
        self.run("make install")

    def package_info(self):
        # Perl module: expose lib path for consumers
        perl5_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl5_lib)
