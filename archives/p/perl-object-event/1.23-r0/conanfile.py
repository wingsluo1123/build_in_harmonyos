#!/usr/bin/env python3
"""Conan recipe — Perl module (ExtUtils::MakeMaker / Makefile.PL).

perl-object-event 1.23-r0 — Object::Event: Perl event callback interface

Runtime dependencies (system Perl modules, not Conan packages):
  - common::sense  (available in system Perl @INC)
  - AnyEvent        (available in system Perl @INC, >= 7.17)
  - Carp            (Perl core module)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlobjecteventConan(ConanFile):
    name = "perl-object-event"
    version = "1.23-r0"
    description = "Object::Event - Perl event callback interface"
    license = "perl"
    homepage = "https://metacpan.org/dist/Object-Event"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps: common::sense, AnyEvent are system-installed Perl modules
        # No Conan dependencies needed
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Use INSTALL_BASE=/ so files install to lib/perl5/ under DESTDIR
        self.run("perl Makefile.PL INSTALL_BASE=/")
        self.run("make -j1")
        # Run tests during build
        self.run("make test")

    def package(self):
        # Install to package folder using DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}")

    def package_info(self):
        # Pure Perl module - no C libraries to link
        self.cpp_info.libs = []
        # Runtime dependencies (system Perl modules)
        self.cpp_info.requires = []
