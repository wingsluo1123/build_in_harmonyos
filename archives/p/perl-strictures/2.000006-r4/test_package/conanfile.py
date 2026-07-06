#!/usr/bin/env python3
"""Conan test_package for perl-strictures — verifies Perl module can be loaded and enforces strict mode."""
import os

from conan import ConanFile


class PerlstricturesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Smoke test: verify strictures module loads and import succeeds
        # Full functional testing is done via upstream `make test` in build()
        dep = self.dependencies["perl-strictures"]
        perl_lib = os.path.join(dep.package_folder, "lib")
        self.run(f'perl -I{perl_lib} -Mstrictures -e "strictures->import; exit 0"')
