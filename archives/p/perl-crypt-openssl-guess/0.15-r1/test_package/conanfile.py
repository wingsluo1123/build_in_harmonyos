#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::Guess (pure Perl module)."""
import os
import glob
import tempfile

from conan import ConanFile


class PerlcryptopensslguessTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-crypt-openssl-guess"]
        pkg_folder = dep.package_folder
        guess_files = glob.glob(os.path.join(pkg_folder, "**", "Crypt", "OpenSSL", "Guess.pm"), recursive=True)
        if not guess_files:
            raise Exception("Crypt/OpenSSL/Guess.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(os.path.dirname(guess_files[0])))
        # Write a simple test script to avoid shell quoting issues
        test_script = os.path.join(tempfile.gettempdir(), "test_crypt_openssl_guess.pl")
        with open(test_script, "w") as f:
            f.write("use Crypt::OpenSSL::Guess;\n")
            f.write("my $inc = openssl_inc_paths();\n")
            f.write("print \"include path: $inc\\n\";\n")
            f.write("print \"OK\\n\";\n")
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib_dir, test_script))
