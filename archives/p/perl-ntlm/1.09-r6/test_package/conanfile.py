#!/usr/bin/env python3
"""Conan test_package for perl-ntlm (Authen::NTLM).

Tests that the Perl module can be loaded and used.
"""
import os

from conan import ConanFile


class PerlntlmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the Perl lib path from the dependency
        dep = self.dependencies["perl-ntlm"]
        perl_lib = os.path.join(dep.package_folder, "lib", "perl5")
        self.output.info("Testing with Perl lib path: " + perl_lib)
        # Test loading the module and printing version
        # Use single quotes for -e to prevent shell variable expansion of $Authen::NTLM::VERSION
        # Use string concatenation (not f-string) to avoid Python interpreting Perl braces as format expressions
        self.run("perl -I" + perl_lib + " -MAuthen::NTLM -e 'print \"Authen::NTLM version: \", $Authen::NTLM::VERSION, chr(10)'")
