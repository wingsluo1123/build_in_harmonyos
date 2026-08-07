#!/usr/bin/env python3
"""Conan recipe for perl-mailtools 2.22 — Perl MailTools module.

MailTools is a pure-Perl module collection (no XS/C extensions).
Build system: perl Makefile.PL (ExtUtils::MakeMaker).
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PerlMailtoolsConan(ConanFile):
    name = "perl-mailtools"
    version = "2.22"
    description = (
        "Various ancient e-mail related modules for Perl, "
        "including Mail::Header, Mail::Internet, Mail::Field, Mail::Mailer"
    )
    license = "GPL-1.0-or-later OR Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/MailTools"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "perl-mailtools supports Linux and OHOS only"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _perl_bin(self):
        """Locate the perl binary from the Conan dependency."""
        dep = self.dependencies.get("perl")
        if dep:
            candidate = os.path.join(dep.package_folder, "bin", "perl")
            if os.path.isfile(candidate):
                return candidate
        perl = os.environ.get("PERL")
        if perl and os.path.isfile(perl):
            return perl
        found = shutil.which("perl")
        if found:
            return found
        return "perl"

    def build(self):
        apply_conandata_patches(self)
        perl = self._perl_bin()
        self.run(
            f"{shlex.quote(perl)} Makefile.PL",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(
            f"make install DESTDIR={shlex.quote(self.package_folder)}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        for pattern in ("Artistic", "Copying"):
            copy(
                self,
                pattern,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        dep = self.dependencies.get("perl")
        perl_ver = str(dep.ref.version) if dep else "5.42.2"

        site_perl = os.path.join(
            self.package_folder, "lib", "perl5", "site_perl", perl_ver
        )
        self.runenv_info.prepend_path("PERL5LIB", site_perl)
        self.buildenv_info.prepend_path("PERL5LIB", site_perl)
