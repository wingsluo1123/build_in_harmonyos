#!/usr/bin/env python3
"""Conan recipe — Perl module JSON::MaybeXS 1.004008.

Pure Perl module using ExtUtils::MakeMaker (perl Makefile.PL).
JSON::MaybeXS is a wrapper that auto-selects the best available JSON backend
(Cpanel::JSON::XS, JSON::XS, or JSON::PP). On OHOS, JSON::PP (core Perl
module) is used as the backend.

No binary artifacts; no static linking needed (R26 N/A for pure Perl).
R32: settings.os check uses `in ("Linux", "OHOS")`
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerljsonmaybexsConan(ConanFile):
    name = "perl-json-maybexs"
    version = "1.004008-r0"
    description = "Wrapper to select the best JSON backend available (XS or PP)"
    license = "Perl Artistic License 2.0"
    homepage = "https://metacpan.org/release/JSON-MaybeXS"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Perl is provided as a system tool (/data/service/hnp/bin/perl 5.42.0)
        # Declaring perl/5.42.2 as a Conan dependency causes version mismatch
        # (Conan package has 5.42.2 libs, system binary is 5.42.0)
        # JSON::PP is a core Perl module, included in system Perl
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Generate Makefile using ExtUtils::MakeMaker
        # PUREPERL_ONLY=1 avoids requiring Cpanel::JSON::XS (not available on OHOS)
        self.run("perl Makefile.PL PUREPERL_ONLY=1")

        # Build (creates blib/lib/JSON/MaybeXS.pm)
        self.run("make -j1")

    def package(self):
        # Copy Perl module files from blib/lib to package lib/
        copy(self, "*.pm", src=os.path.join(self.build_folder, "blib", "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no libraries to link
        perl_lib = os.path.join(self.package_folder, "lib")
        self.output.info(f"Perl library path: {perl_lib}")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
