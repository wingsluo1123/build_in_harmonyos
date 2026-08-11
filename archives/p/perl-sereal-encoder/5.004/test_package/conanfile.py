#!/usr/bin/env python3
"""Conan test_package for perl-sereal-encoder 5.004 (Perl XS module).

L1 test: verify the Perl module files are present and valid.
Full verification: file existence + Perl syntax + ELF format + .codesign
signature + symbol table + module metadata.

Note: .so loading is restricted on HarmonyOS due to file permission model
(perl runs as UID 20020101, conan-built .so owned by UID 20001006, chmod
ineffective per E046). File-based verification is used instead.
"""
import os

from conan import ConanFile


class PerlSerealEncoderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["perl-sereal-encoder"]
        pkg = dep.package_folder
        arch = str(self.settings.arch)
        test_script = os.path.join(os.path.dirname(__file__), "test_encoder.py")
        self.run(f'python3 "{test_script}" "{pkg}" "{arch}"')
