#!/usr/bin/env python3
"""Conan recipe — Perl module (ExtUtils::MakeMaker / Makefile.PL).

perl-object-event 1.23-r0 — Object::Event: Perl event callback interface

Runtime dependencies (Perl modules, not Conan packages):
  - common::sense  (user-installed, not in system Perl @INC)
  - AnyEvent        (user-installed, not in system Perl @INC)
  - Carp            (Perl core module)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


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
        # Runtime deps: common::sense, AnyEvent are user-installed Perl modules
        # (not Conan packages, not in system Perl @INC in CI)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Use INSTALL_BASE=/ so files install to lib/perl5/ under DESTDIR
        self.run("perl Makefile.PL INSTALL_BASE=/")
        self.run("make -j1")

    def package(self):
        # Install to package folder using DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}")

    def package_info(self):
        # Pure Perl module - no C libraries to link
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers (test_package) can find Object::Event
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
        # Inject system Perl module paths for runtime deps (common::sense, AnyEvent)
        # These are user-installed Perl modules not managed by Conan.
        # CI workers can set SYSTEM_PERL5LIB; auto-detect common install locations as fallback.
        system_perl5lib = os.environ.get("SYSTEM_PERL5LIB", "")
        if not system_perl5lib:
            candidates = [
                os.path.join(os.path.expanduser("~"), "usr", "local", "lib", "perl5", "aarch64-linux"),
                os.path.join(os.path.expanduser("~"), "usr", "local", "lib", "perl5"),
            ]
            system_perl5lib = ":".join(p for p in candidates if os.path.isdir(p))
        if system_perl5lib:
            for p in system_perl5lib.split(":"):
                if p:
                    self.runenv_info.append_path("PERL5LIB", p)
