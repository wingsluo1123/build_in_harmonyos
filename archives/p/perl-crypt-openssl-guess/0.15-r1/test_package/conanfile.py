#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::Guess (pure Perl module)."""
import os

from conan import ConanFile


class PerlcryptopensslguessTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # PERL5LIB is set by runenv_info from the package's package_info()
        test_script = os.path.join(self.recipe_folder, "test_crypt_openssl_guess.pl")
        self.run(f'perl "{test_script}"', env="conanrun")
