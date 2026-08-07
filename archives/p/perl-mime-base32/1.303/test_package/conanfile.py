#!/usr/bin/env python3
"""Conan test_package — Perl module MIME::Base32.

Verifies the installed Perl module can be loaded and used for
encode/decode round-trip operations.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Perlmimebase32TestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["perl-mime-base32"]
        perl_lib = os.path.join(dep.package_folder, "lib")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{perl_lib}"')
