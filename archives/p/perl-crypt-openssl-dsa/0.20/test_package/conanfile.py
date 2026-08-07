#!/usr/bin/env python3
"""test_package for Crypt-OpenSSL-DSA — verifies DSA.so and DSA.pm.

R34: Test must substantially depend on the tested package.
This test calls test_dsa.sh which verifies:
1. DSA.pm is syntactically valid Perl (perl -c)
2. DSA.so is a valid ELF shared object (file)
3. DSA.so contains the XS bootstrap function (readelf -s)
4. DSA.so links against OpenSSL libcrypto (readelf -d)
"""
import os

from conan import ConanFile


class CryptOpenSSLDSATestConan(ConanFile):
    """test_package for Crypt-OpenSSL-DSA — verifies XS module build."""

    test_type = "explicit"

    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-crypt-openssl-dsa"]
        pkg_folder = dep.package_folder
        test_script = os.path.join(self.source_folder, "test_dsa.sh")
        self.run(f'sh "{test_script}" "{pkg_folder}"', env="conanrun")
